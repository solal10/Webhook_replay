import logging
from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from app.celery_app import celery
from app.db import models
from app.tasks import BASE_DELAY, MAX_ATTEMPTS, forward_event
from freezegun import freeze_time
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def celery_worker():
    celery.conf.task_always_eager = True
    celery.conf.task_eager_propagates = True
    yield
    celery.conf.task_always_eager = False


def test_retry_scheduling(db: Session, respx_mock):
    # Create test data
    tenant = models.Tenant(name="test", token="test_token")
    db.add(tenant)
    db.flush()

    target = models.Target(tenant_id=tenant.id, url="http://example.com")
    db.add(target)
    db.flush()

    event = models.Event(
        tenant_id=tenant.id, payload={"test": "data"}, sha256="test_hash"
    )
    db.add(event)
    db.commit()
    logger.info(f"Created event with ID {event.id}")

    # Mock the HTTP request to fail
    respx_mock.post("http://example.com").mock(return_value=httpx.Response(500))

    # Commit all changes
    db.commit()

    # Freeze time for deterministic testing
    with freeze_time("2025-01-01 12:00:00"):
        forward_event(str(event.id), session=db)

    # Check delivery was created with retry info
    delivery = db.query(models.Delivery).first()
    assert delivery is not None
    assert delivery.attempts == 1
    assert delivery.status == 500
    assert delivery.next_run == datetime(
        2025, 1, 1, 12, 0, 30, tzinfo=UTC
    )  # Now + BASE_DELAY


def test_backoff_doubles(db: Session, respx_mock):
    # Create test data
    tenant = models.Tenant(name="test", token="test_token")
    db.add(tenant)
    db.flush()

    target = models.Target(tenant_id=tenant.id, url="http://example.com")
    db.add(target)
    db.flush()

    event = models.Event(
        tenant_id=tenant.id, payload={"test": "data"}, sha256="test_hash"
    )
    db.add(event)
    db.commit()
    logger.info(f"Created event with ID {event.id}")

    # Mock the HTTP request to fail twice
    respx_mock.post("http://example.com").mock(return_value=httpx.Response(500))

    # First attempt
    with freeze_time("2025-01-01 12:00:00"):
        forward_event(str(event.id), session=db)

    # Second attempt
    with freeze_time("2025-01-01 12:00:30"):
        forward_event(str(event.id), attempt=2, session=db)

    # Check deliveries
    deliveries = db.query(models.Delivery).order_by(models.Delivery.attempts).all()
    assert len(deliveries) == 2

    # First delivery should have next_run at +30s
    assert deliveries[0].next_run == datetime(2025, 1, 1, 12, 0, 30, tzinfo=UTC)

    # Second delivery should have next_run at +60s
    assert deliveries[1].next_run == datetime(2025, 1, 1, 12, 1, 30, tzinfo=UTC)


def test_give_up_after_max(db: Session, respx_mock):
    # Create test data
    tenant = models.Tenant(name="test", token="test_token")
    db.add(tenant)
    db.flush()

    target = models.Target(tenant_id=tenant.id, url="http://example.com")
    db.add(target)
    db.flush()

    event = models.Event(
        tenant_id=tenant.id, payload={"test": "data"}, sha256="test_hash"
    )
    db.add(event)
    db.commit()
    logger.info(f"Created event with ID {event.id}")

    # Mock the HTTP request to always fail
    respx_mock.post("http://example.com").mock(return_value=httpx.Response(500))

    # Make all attempts
    current_time = datetime(2025, 1, 1, 12, 0, 0)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        with freeze_time(current_time):
            forward_event(str(event.id), attempt=attempt, session=db)
        current_time += timedelta(seconds=BASE_DELAY * (2 ** (attempt - 1)))

    # Check we have exactly MAX_ATTEMPTS deliveries
    deliveries = db.query(models.Delivery).order_by(models.Delivery.attempts).all()
    assert len(deliveries) == MAX_ATTEMPTS

    # Last delivery should not have next_run set
    assert deliveries[-1].next_run is None
