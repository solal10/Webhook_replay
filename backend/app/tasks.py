import httpx
from app.celery_app import celery
from app.db import models
from app.db.session import SessionLocal


@celery.task(bind=True, autoretry_for=(Exception,), retry_backoff=2, max_retries=3)
def forward_event(self, event_id: str, session=None):
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

        ev = session.get(models.Event, event_id)
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
        if tgt.headers:
            headers = tgt.headers

        r = httpx.post(tgt.url, json=ev.payload, headers=headers)
        delivered = models.Delivery(
            event_id=ev.id, status=r.status_code, response=r.text
        )
        session.add(delivered)
        session.commit()
        return {"status": r.status_code}
    finally:
        if should_close:
            session.close()
