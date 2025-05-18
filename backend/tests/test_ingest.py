import hashlib
import hmac
import json
import time

from app.db.session import SessionLocal
from app.main import app, get_settings
from fastapi.testclient import TestClient

client = TestClient(app)
settings = get_settings()


def _stripe_header(body: bytes, secret: str):
    ts = int(time.time())
    payload = f"{ts}.{body.decode()}".encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def test_ingest_creates_event():
    # create tenant & key
    db = SessionLocal()
    try:
        from app.db import crud, models, schemas

        tenant = crud.create_tenant(db, schemas.TenantCreate(name="StripeUser"))
        db.commit()

        body = json.dumps(
            {"id": "evt_123", "type": "payment_intent.succeeded"}
        ).encode()
        headers = {
            "Stripe-Signature": _stripe_header(body, settings.stripe_signing_secret)
        }
        r = client.post(f"/in/{tenant.token}", data=body, headers=headers)
        assert r.status_code == 200

        # Verify event was created
        event = db.query(models.Event).filter_by(tenant_id=tenant.id).first()
        assert event is not None
        assert event.duplicate is False

        # second hit with same payload should be marked as duplicate
        r2 = client.post(f"/in/{tenant.token}", data=body, headers=headers)
        assert r2.status_code == 409  # Conflict for duplicate event
    finally:
        db.close()
