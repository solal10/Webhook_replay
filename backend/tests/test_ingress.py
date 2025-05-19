import hashlib
import json
import time

import pytest
import stripe
from app.db import models


def test_valid_token_ingestion(client, test_tenant, mock_aws_s3):
    # Set up Stripe signing secret
    test_tenant.stripe_signing_secret = "whsec_test"

    # Create payload and signature
    payload = {"event": "example", "id": "evt_001"}
    timestamp = int(time.time())
    payload_str = json.dumps(payload)
    signature = stripe.WebhookSignature._compute_signature(
        f"{timestamp}.{payload_str}", test_tenant.stripe_signing_secret
    )
    stripe_sig = f"t={timestamp},v1={signature}"

    # Send request
    response = client.post(
        f"/in/{test_tenant.token}",
        json=payload,
        headers={"Stripe-Signature": stripe_sig},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "received"}


def test_ingest_invalid_signature(client, test_tenant, mock_aws_s3):
    # Set up Stripe signing secret
    test_tenant.stripe_signing_secret = "whsec_test"

    # Create payload with invalid signature
    payload = {"event": "example", "id": "evt_001"}
    timestamp = int(time.time())
    stripe_sig = f"t={timestamp},v1=invalid_signature"

    # Send request
    response = client.post(
        f"/in/{test_tenant.token}",
        json=payload,
        headers={"Stripe-Signature": stripe_sig},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Stripe signature"}


def test_ingest_missing_signature(client, test_tenant, mock_aws_s3):
    # Set up Stripe signing secret
    test_tenant.stripe_signing_secret = "whsec_test"

    # Send request without signature
    payload = {"event": "example", "id": "evt_001"}
    response = client.post(f"/in/{test_tenant.token}", json=payload)
    assert response.status_code == 400
    assert response.json() == {"detail": "Missing Stripe signature"}


def test_invalid_token_ingestion(client):
    response = client.post("/in/wrongtoken", json={"event": "example"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_malformed_json(client, test_tenant):
    # Create a valid signature for the malformed payload
    timestamp = int(time.time())
    signature = stripe.WebhookSignature._compute_signature(
        f"{timestamp}.{{invalid json}}", test_tenant.stripe_signing_secret
    )
    stripe_sig = f"t={timestamp},v1={signature}"

    response = client.post(
        f"/in/{test_tenant.token}",
        headers={"Content-Type": "application/json", "Stripe-Signature": stripe_sig},
        data="{invalid json}",
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid JSON payload"}


def test_duplicate_event_detection(client, test_tenant, db, mock_aws_s3):
    import logging

    logger = logging.getLogger(__name__)

    # First request
    payload = {"event": "test.payment", "id": "evt_001"}
    payload_str = json.dumps(payload)
    timestamp = int(time.time())
    signature = stripe.WebhookSignature._compute_signature(
        f"{timestamp}.{payload_str}", test_tenant.stripe_signing_secret
    )
    stripe_sig = f"t={timestamp},v1={signature}"

    logger.info(f"Making first request with token {test_tenant.token}")
    response1 = client.post(
        f"/in/{test_tenant.token}",
        json=payload,
        headers={"Stripe-Signature": stripe_sig},
    )
    logger.info(f"First response: {response1.status_code} - {response1.text}")
    assert response1.status_code == 200

    # Same event again
    response2 = client.post(
        f"/in/{test_tenant.token}",
        json=payload,
        headers={"Stripe-Signature": stripe_sig},
    )
    assert response2.status_code == 409  # Conflict for duplicate event

    # Verify only one event is stored
    events = db.query(models.Event).filter_by(tenant_id=test_tenant.id).all()
    logger.info(f"Found {len(events)} events")
    for i, event in enumerate(events):
        logger.info(
            f"Event {i}: hash={event.hash}, content_hash={event.content_hash}, duplicate={event.duplicate}"
        )
    assert len(events) == 1  # Only one event should be stored
    assert events[0].duplicate == False  # And it should not be marked as duplicate


def test_empty_payload(client, test_tenant):
    # Create a valid signature for the empty payload
    timestamp = int(time.time())
    signature = stripe.WebhookSignature._compute_signature(
        f"{timestamp}.{{}}", test_tenant.stripe_signing_secret
    )
    stripe_sig = f"t={timestamp},v1={signature}"

    response = client.post(
        f"/in/{test_tenant.token}", json={}, headers={"Stripe-Signature": stripe_sig}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Empty payload not allowed"}


def test_large_payload(client, test_tenant):
    # Create a payload that's too large (>1MB)
    large_payload = {"data": "x" * (1024 * 1024 + 1)}
    response = client.post(f"/in/{test_tenant.token}", json=large_payload)
    assert response.status_code == 413
    assert response.json() == {"detail": "Payload too large"}
