import logging
import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
from app.celery_app import celery
from app.db import models
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Constants for retry logic
BASE_DELAY = 30  # seconds
MAX_ATTEMPTS = 5

# Use test database if available
test_db_url = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webhooks_test"
)
os.environ["DATABASE_URL"] = test_db_url


@celery.task(bind=True)
def forward_event(self, event_id: str, attempt: int = 1, session=None):
    logger.info(
        f"Starting forward_event task with event_id={event_id}, attempt={attempt}"
    )
    if self.request.id:
        logger.info(f"Task ID: {self.request.id}")
    if session is None:
        session = SessionLocal()
        should_close = True
    else:
        should_close = False

    try:
        # Convert string ID to integer
        try:
            event_id = int(event_id)
        except (TypeError, ValueError):
            raise ValueError("Invalid event ID")

        logger.info(f"Looking for event with ID {event_id}")
        ev = session.query(models.Event).filter_by(id=event_id).first()
        logger.info(f"Found event: {ev}")
        if not ev:
            raise ValueError("Event not found")

        tgt = (
            session.query(models.Target)
            .filter_by(tenant_id=ev.tenant_id, provider="stripe")
            .first()
        )
        if not tgt:
            raise ValueError("No target defined")

        # Parse headers from JSON string if present
        headers = {}
        headers = tgt.headers or {}

        try:
            r = httpx.post(tgt.url, json=ev.payload, headers=headers, timeout=10)
            success = 200 <= r.status_code < 300
        except Exception as exc:
            success = False
            r = SimpleNamespace(status_code=0, text=str(exc))

        # Get the latest delivery attempt for this event
        latest_delivery = (
            session.query(models.Delivery)
            .filter_by(event_id=ev.id)
            .order_by(models.Delivery.created_at.desc())
            .first()
        )
        logger.info(f"Latest delivery: {latest_delivery}")
        logger.info(f"Current attempt: {attempt}")

        # Create a new delivery attempt
        delivery = models.Delivery(
            event_id=ev.id, attempts=attempt, status=r.status_code, response=r.text
        )

        # If the response status is not 2xx, schedule a retry
        if not success and attempt < MAX_ATTEMPTS:
            # Calculate next retry time with exponential backoff
            backoff = BASE_DELAY * (2 ** (attempt - 1))  # 30s, 60s, 120s, ...
            next_run = datetime.now(UTC) + timedelta(seconds=backoff)
            delivery.next_run = next_run

            # Schedule the next retry
            forward_event.apply_async(args=[event_id, attempt + 1], eta=next_run)

        session.add(delivery)
        session.commit()
        return {"status": r.status_code}
    finally:
        if should_close:
            session.close()
