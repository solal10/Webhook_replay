import hashlib
import hmac
import json
import time

from app.core.config import Settings
from app.db import crud, models, schemas
from app.db.session import SessionLocal
from app.main import app, get_settings
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def _stripe_header(body: bytes, secret: str):
    import logging

    logger = logging.getLogger(__name__)
    ts = int(time.time())
    payload = f"{ts}.{body.decode()}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    logger.info(f"Test signature: {sig}")
    logger.info(f"Test secret: {secret}")
    return f"t={ts},v1={sig}"


def test_ingest_creates_event(client: TestClient, db: Session, settings: Settings):
    # Create tenant
    tenant = crud.create_tenant(db, schemas.TenantCreate(name="test_tenant"))
    tenant.stripe_signing_secret = settings.stripe_signing_secret
    db.commit()

    payload = {"id": "evt_123", "type": "payment_intent.succeeded"}
    body = json.dumps(payload).encode()
    headers = {
        "Stripe-Signature": _stripe_header(body, settings.stripe_signing_secret),
        "Content-Type": "application/json",
    }
    r = client.post(f"/in/{tenant.token}", content=body, headers=headers)
    assert r.status_code == 200

    # Verify event was created
    event = db.query(models.Event).filter_by(tenant_id=tenant.id).first()
    assert event is not None
    assert event.duplicate is False

    # second hit with same payload should be marked as duplicate
    r2 = client.post(f"/in/{tenant.token}", content=body, headers=headers)
    assert r2.status_code == 409  # Conflict for duplicate event
