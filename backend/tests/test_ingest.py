import hashlib
import hmac
import json
import time
from unittest.mock import MagicMock

import pytest
from app.core.config import Settings
from app.db import crud, models, schemas
from app.db.session import SessionLocal
from app.main import app, get_s3_client, get_settings
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def s3_client():
    mock = MagicMock()
    app.dependency_overrides[get_s3_client] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_s3_client)


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
    assert event.sha256 == hashlib.sha256(body).hexdigest()
    assert event.payload == payload

    # second hit with same payload should be marked as duplicate
    r2 = client.post(f"/in/{tenant.token}", content=body, headers=headers)
    assert r2.status_code == 200  # Returns 200 for duplicates

    # Verify no duplicate event was created
    events = db.query(models.Event).filter_by(tenant_id=tenant.id).all()
    assert len(events) == 1  # No duplicate event should be created


def test_s3_upload(
    client: TestClient, db: Session, settings: Settings, s3_client: MagicMock
):
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

    # Verify S3 upload
    s3_client.put_object.assert_called_once_with(
        Bucket=settings.events_bucket,
        Key=f"{tenant.id}/{event.sha256}.json",
        Body=body,
        ContentType="application/json",
    )

    # Verify payload
    assert event.payload == payload
