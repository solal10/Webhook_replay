import hashlib
import json
from datetime import UTC, datetime

import boto3
import stripe
from app.core.config import get_settings
from app.db import crud, models, schemas
from app.db.session import SessionLocal
from app.services import stripe_verify
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from stripe.error import SignatureVerificationError

app = FastAPI()
bearer_scheme = HTTPBearer()

# Maximum payload size (1MB)
MAX_PAYLOAD_SIZE = 1024 * 1024


# ---------- dependency ----------
def db_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
    )


def current_tenant(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(db_session),
) -> models.Tenant:
    tenant = crud.verify_api_key(db, creds.credentials)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return tenant


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "settings": {
            "database_url": get_settings().database_url,
            "stripe_signing_secret": get_settings().stripe_signing_secret,
            "aws_region": get_settings().aws_region,
            "s3_bucket": get_settings().s3_bucket,
        },
    }


# ---------- signup ----------
@app.post("/signup")
def signup(data: schemas.TenantCreate, db: Session = Depends(db_session)):
    tenant = crud.create_tenant(db, data)
    api_key = crud.issue_api_key(db, tenant.id)
    db.commit()
    return {
        "tenant": {"id": tenant.id, "name": tenant.name, "token": tenant.token},
        "api_key": api_key,
        "ingress_url": f"https://hooks.local/in/{tenant.token}",
    }


# ---------- whoami ----------
@app.get("/me")
def who_am_i(tenant: models.Tenant = Depends(current_tenant)):
    return {"id": tenant.id, "name": tenant.name, "token": tenant.token}


# ---------- ingress ----------
@app.post("/in/{token}")
async def ingest_webhook(
    token: str, request: Request, db: Session = Depends(db_session)
):
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Received webhook for token: {token}")
    # Look up tenant by token
    logger.info(f"Looking up tenant with token {token} using session {id(db)}")
    tenant: models.Tenant | None = (
        db.query(models.Tenant).filter_by(token=token).first()
    )
    logger.info(f"Found tenant: {tenant is not None}")
    if not tenant:
        # Commit any pending changes to make sure we have the latest data
        db.commit()
        tenant = db.query(models.Tenant).filter_by(token=token).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Not Found")

    # Check payload size
    content_length = request.headers.get("content-length", 0)
    if int(content_length) > MAX_PAYLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Payload too large")

    # Read request body first
    try:
        logger.info("Reading request body...")
        raw = await request.body()
        logger.info("Request body read successfully")

        # Check for empty payload
        if not raw:
            raise HTTPException(status_code=400, detail="Empty payload not allowed")

        # Verify Stripe signature before parsing JSON
        logger.info("Checking for Stripe signature...")
        stripe_sig = request.headers.get("Stripe-Signature") or request.headers.get(
            "stripe-signature"
        )
        logger.info(f"Stripe signature present: {stripe_sig is not None}")

        if not stripe_sig:
            raise HTTPException(status_code=400, detail="Missing Stripe signature")

        if not tenant.stripe_signing_secret:
            logger.warning(
                f"Tenant {tenant.id} has no Stripe signing secret configured"
            )
            raise HTTPException(
                status_code=400, detail="Stripe webhooks not configured"
            )

        try:
            # Verify the event
            stripe.Webhook.construct_event(
                payload=raw,
                sig_header=stripe_sig,
                secret=tenant.stripe_signing_secret,
                tolerance=300,
            )
        except SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")

        # Parse JSON payload after signature verification
        try:
            logger.info("Parsing JSON payload...")
            payload = json.loads(raw)
            logger.info("JSON payload parsed successfully")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        # Check for empty payload
        if not payload:
            raise HTTPException(status_code=400, detail="Empty payload not allowed")

        # Generate hash for duplicate detection
        payload_hash = hashlib.sha256(raw).hexdigest()

        # Store payload in S3 or locally in development
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        s3_key = f"{tenant.id}/{timestamp}_{payload_hash}.json"

        try:
            s3 = get_s3_client()
            s3.put_object(
                Bucket=get_settings().s3_bucket,
                Key=s3_key,
                Body=raw,
                ContentType="application/json",
            )
        except Exception as e:
            # In development, store locally
            import pathlib

            payload_dir = pathlib.Path(__file__).parent.parent / "payloads"
            payload_dir.mkdir(exist_ok=True)
            local_path = payload_dir / s3_key
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(raw)

        # We use two hashes:
        # 1. content_hash: based only on the payload content, used for duplicate detection
        # 2. unique_hash: includes timestamp and a random component, used as the event's unique identifier
        content_hash = hashlib.sha256(raw).hexdigest()
        import uuid

        unique_hash = hashlib.sha256(
            f"{raw}_{timestamp}_{uuid.uuid4()}".encode()
        ).hexdigest()

        # Check for duplicates and store event in database
        existing_event = (
            db.query(models.Event)
            .filter_by(tenant_id=tenant.id, content_hash=content_hash)
            .first()
        )

        if existing_event:
            raise HTTPException(
                status_code=409,
                detail={
                    "status": "duplicate",
                    "original_event_id": existing_event.id,
                },
            )

        event = models.Event(
            tenant_id=tenant.id,
            provider="stripe",  # TODO: Make this configurable
            event_type=payload.get("type", "unknown"),
            payload_path=s3_key,
            hash=unique_hash,  # Use the unique hash for the event
            content_hash=content_hash,  # Store the content hash for duplicate detection
            duplicate=False,  # No need to mark as duplicate since we return 409
        )
        db.add(event)
        db.commit()

        return {"status": "received"}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
