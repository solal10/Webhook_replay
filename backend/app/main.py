import hashlib
import json
import pathlib

from app.core.config import get_settings
from app.db import crud, models, schemas
from app.db.session import SessionLocal
from app.services import stripe_verify
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

app = FastAPI()
bearer_scheme = HTTPBearer()


# ---------- dependency ----------
def db_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
PAYLOAD_DIR = pathlib.Path(__file__).parent.parent / "payloads"
PAYLOAD_DIR.mkdir(exist_ok=True)


@app.post("/in/{token}")
async def ingest_webhook(
    token: str, request: Request, db: Session = Depends(db_session)
):
    tenant: models.Tenant | None = (
        db.query(models.Tenant).filter_by(token=token).first()
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Unknown tenant token")

    raw = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature")

    try:
        stripe_verify.verify(raw, sig_header, get_settings().stripe_signing_secret)
    except stripe_verify.StripeSignatureError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # hash + duplicate detection
    hash_hex = hashlib.sha256(raw).hexdigest()
    existing_event = (
        db.query(models.Event).filter_by(tenant_id=tenant.id, hash=hash_hex).first()
    )
    if existing_event:
        return Response(
            status_code=409, content=json.dumps({"detail": "Duplicate event"})
        )

    event = models.Event(
        tenant_id=tenant.id,
        provider="stripe",
        event_type=json.loads(raw)["type"],
        payload_path=str(PAYLOAD_DIR / f"{hash_hex}.json"),
        hash=hash_hex,
        duplicate=False,
    )
    db.add(event)
    db.commit()

    # save blob to disk
    (PAYLOAD_DIR / f"{hash_hex}.json").write_bytes(raw)

    # Acknowledge to Stripe
    return Response(status_code=200)
