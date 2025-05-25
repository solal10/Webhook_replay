import pytest
import respx
from app.db import models
from app.tasks import forward_event
from httpx import Response


def test_forward_event_success(db, respx_mock):
    # Create test data
    tenant = models.Tenant(name="Test Tenant", token="test_token")
    db.add(tenant)

    target = models.Target(
        tenant_id=tenant.id,
        url="https://example.com/webhook",
        headers={"X-Test": "test"},
    )
    db.add(target)

    event = models.Event(
        tenant_id=tenant.id,
        sha256="test_hash",
        payload={"test": "data"},
        duplicate=False,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Mock the webhook endpoint
    respx_mock.post("https://example.com/webhook").mock(
        return_value=Response(200, text="OK")
    )

    # Run the task synchronously
    result = forward_event.apply(args=[str(event.id)], kwargs={"session": db}).get()

    # Verify the result
    assert result["status"] == 200

    # Check delivery was recorded
    delivery = db.query(models.Delivery).filter_by(event_id=event.id).first()
    assert delivery is not None
    assert delivery.status == 200
    assert delivery.response == "OK"


def test_forward_event_no_target(db):
    # Create test data without target
    tenant = models.Tenant(name="Test Tenant", token="test_token")
    db.add(tenant)

    event = models.Event(
        tenant_id=tenant.id,
        sha256="test_hash",
        payload={"test": "data"},
        duplicate=False,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Run the task and expect ValueError
    with pytest.raises(ValueError, match="No target defined"):
        forward_event.apply(args=[str(event.id)], kwargs={"session": db}).get()

    # Verify no delivery was recorded
    delivery = db.query(models.Delivery).filter_by(event_id=event.id).first()
    assert delivery is None
