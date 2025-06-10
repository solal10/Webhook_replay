import hashlib
import json
from datetime import UTC, datetime

import boto3
import redis.asyncio as redis
import stripe
from app.core.config import get_settings
from app.db import crud, models, schemas
from app.db.session import SessionLocal
from app.services import stripe_verify
from app.tasks import forward_event
from app.storage.boot_s3 import ensure_secure_bucket
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.orm import Session
from stripe.error import SignatureVerificationError
from fastapi.middleware.cors import CORSMiddleware
from app.middleware.body_size import BodySizeLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.schemas.ingest import WebhookPayload
from pydantic import ValidationError
import logging
import sqlalchemy.exc

app = FastAPI(
    title="Webhook Replay Service",
    description="A service for replaying webhooks",
    version="1.0.0",
    dependencies=[Depends(RateLimiter(times=100, seconds=60))],  # Global rate limit
)
bearer_scheme = HTTPBearer()

# Maximum payload size (1MB)
MAX_PAYLOAD_SIZE = 1024 * 1024

# CORS lockdown: allow * in dev, restrict in prod
settings = get_settings()

# Add body size middleware
app.add_middleware(BodySizeLimitMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware using settings.allowed_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    try:
        # Initialize rate limiter
        redis_conn = redis.from_url(settings.redis_url, decode_responses=True)
        await FastAPILimiter.init(redis_conn)

        # Initialize S3 bucket with security settings
        ensure_secure_bucket()
    except Exception as e:
        print(f"Warning: Failed to initialize services: {e}")
        # Continue without rate limiting


logger = logging.getLogger(__name__)


# ---------- dependency ----------
def db_session():
    try:
        db: Session = SessionLocal()
        logger.info("Database session created successfully")
        try:
            yield db
        finally:
            db.close()
            logger.info("Database session closed")
    except Exception as e:
        if isinstance(e, (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.DBAPIError)):
            logger.error(f"Database error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection failed",
            )
        raise  # Re-raise non-database exceptions


def get_s3_client():
    settings = get_settings()
    s3 = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        endpoint_url=settings.aws_endpoint_url,
    )
    return s3


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


@app.get("/health", include_in_schema=False)
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "settings": {
            "database_url": settings.database_url,
            "stripe_signing_secret": settings.stripe_signing_secret,
            "aws_region": settings.aws_region,
            "events_bucket": settings.events_bucket,
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


# ---------- targets ----------
@app.post(
    "/targets", response_model=schemas.TargetOut, status_code=status.HTTP_201_CREATED
)
def create_target(
    data: schemas.TargetCreate,
    tenant: models.Tenant = Depends(current_tenant),
    db: Session = Depends(db_session),
):
    target = crud.upsert_target(db, tenant.id, data)
    db.commit()
    return target


# ---------- stripe ----------
@app.put("/tenants/{token}/stripe")
def set_stripe_secret(
    token: str, data: schemas.StripeSecretUpdate, db: Session = Depends(db_session)
):
    tenant = db.query(models.Tenant).filter_by(token=token).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Not Found")
    tenant.stripe_signing_secret = data.signing_secret
    db.commit()
    return {"status": "ok"}


# ---------- events ----------
@app.post(
    "/events/{event_id}/replay",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=schemas.EventReplayResponse,
    description="Replay any stored event. Requires your API key.",
)
def replay_event(
    event_id: int,
    tenant: models.Tenant = Depends(current_tenant),
    db: Session = Depends(db_session),
):
    # Fetch the event
    event = db.query(models.Event).filter_by(id=event_id).first()
    if not event or event.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Event not found")

    # Create a new delivery record
    delivery = models.Delivery(
        event_id=event.id, attempts=0, status=0, response="manual replay"  # queued
    )
    db.add(delivery)
    db.commit()

    # Queue the event for delivery
    forward_event.delay(str(event.id), attempt=1)

    return {"status": "queued", "event_id": event.id}


# ---------- ingress ----------
@app.post(
    "/in/{token}",
    dependencies=[Depends(RateLimiter(times=30, seconds=60))],  # Per-tenant rate limit
)
async def ingest_webhook(
    token: str,
    request: Request,
    db: Session = Depends(db_session),
    s3_client: boto3.client = Depends(get_s3_client),
):
    logger.info(f"Received webhook for token: {token}")

    # Check for empty payload
    content_length = request.headers.get("content-length", "0")
    if content_length == "0":
        raise HTTPException(status_code=400, detail="Empty JSON body")

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

    try:
        # Read and parse request body
        raw = await request.body()
        if not raw:
            raise HTTPException(status_code=400, detail="Empty JSON body")

        # Parse and validate payload
        try:
            payload = WebhookPayload.model_validate_json(raw)
        except ValidationError as ve:
            raise HTTPException(status_code=400, detail=ve.errors())

        # Convert payload to JSON string for storage
        raw = payload.model_dump_json().encode()
        raw_str = raw.decode()
        logger.info(f"Raw body str: {raw_str}")
        logger.info(f"Raw body bytes: {raw}")
        logger.info(f"Raw body repr: {repr(raw_str)}")

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

        # Verify event signature
        try:
            logger.info(f"Tenant stripe_signing_secret: {tenant.stripe_signing_secret}")
            # Verify the event
            stripe_verify.verify(
                raw_body=raw,
                header=stripe_sig,
                secret=tenant.stripe_signing_secret,
                tolerance=300,
            )
            logger.info("Stripe signature verification successful")
        except stripe_verify.StripeSignatureError:
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")

        # Compute SHA-256 hash
        sha256 = hashlib.sha256(raw).hexdigest()

        # Check if event already exists
        existing_event = (
            db.query(models.Event).filter_by(tenant_id=tenant.id, sha256=sha256).first()
        )
        if not existing_event:
            event = models.Event(
                tenant_id=tenant.id,
                sha256=sha256,
                payload=payload.model_dump(),
                duplicate=False,
            )
            db.add(event)
            db.commit()

            # Queue event for delivery
            logger.info(f"Queuing event {event.id} for delivery")
            logger.info(
                f"Event data: tenant_id={event.tenant_id}, sha256={event.sha256}"
            )
            try:
                result = forward_event.delay(str(event.id), 1)
                logger.info(f"Task queued with ID {result.id}")
                logger.info(f"Task result type: {type(result)}")
                logger.info(f"Task result details: {result.__dict__}")
            except Exception as e:
                logger.error(f"Failed to queue task: {e}", exc_info=True)

            # Upload payload to S3
            settings = get_settings()
            s3_key = f"{tenant.id}/{sha256}.json"

            try:
                s3_client.put_object(
                    Bucket=settings.events_bucket,
                    Key=s3_key,
                    Body=raw,
                    ContentType="application/json",
                )
            except Exception as e:
                logger.error(f"Failed to upload payload to S3: {e}")
                # Continue despite S3 error

        return {"status": "received"}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
