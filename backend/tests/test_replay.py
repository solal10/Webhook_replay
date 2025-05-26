import pytest
from app.db import models
from fastapi import status
from passlib.hash import bcrypt


def test_replay_success(client, db, test_tenant, monkeypatch):
    # Create test data
    event = models.Event(
        tenant_id=test_tenant.id, payload={"test": "data"}, sha256="test_hash"
    )
    db.add(event)
    db.commit()

    # Patch Celery to eager mode
    monkeypatch.setattr("app.tasks.forward_event.delay", lambda *args, **kwargs: None)

    # Send replay request
    response = client.post(
        f"/events/{event.id}/replay",
        headers={"Authorization": "Bearer test_key"},
    )

    # Check response
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"status": "queued", "event_id": event.id}

    # Check delivery record
    delivery = db.query(models.Delivery).filter_by(event_id=event.id).first()
    assert delivery is not None
    assert delivery.attempts == 0
    assert delivery.status == 0
    assert delivery.response == "manual replay"


def test_replay_unauthorized(client, db, test_tenant):
    # Create test data for tenant A
    event_a = models.Event(
        tenant_id=test_tenant.id, payload={"test": "data"}, sha256="test_hash_a"
    )
    db.add(event_a)

    # Create tenant B
    tenant_b = models.Tenant(
        name="tenant_b", token="def456", stripe_signing_secret="whsec_test_b"
    )
    db.add(tenant_b)
    db.commit()

    # Create API key for tenant B
    api_key_b = models.ApiKey(
        tenant_id=tenant_b.id, hashed_key=bcrypt.hash("test_key_b")
    )
    db.add(api_key_b)
    db.commit()

    # Try to replay tenant A's event with tenant B's API key
    response = client.post(
        f"/events/{event_a.id}/replay",
        headers={"Authorization": "Bearer test_key_b"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Event not found"}


def test_replay_not_found(client, db, test_tenant):
    # Try to replay non-existent event
    response = client.post(
        "/events/999/replay",
        headers={"Authorization": "Bearer test_key"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Event not found"}
