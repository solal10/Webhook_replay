import json
from unittest.mock import patch

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
async def setup_redis():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    with patch("fastapi_limiter.FastAPILimiter.init") as mock_init:
        mock_init.return_value = None
        with patch("fastapi_limiter.FastAPILimiter.redis", redis):
            yield


def test_rate_limit_ip(client):
    # Send 101 requests quickly
    for _ in range(100):
        response = client.get("/health")
        assert response.status_code == 200

    # The 101st request should be rate limited
    response = client.get("/health")
    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}


def test_rate_limit_tenant(client):
    # Create a test tenant
    response = client.post(
        "/signup",
        json={"name": "Test Tenant", "email": "test@example.com"},
    )
    assert response.status_code == 200
    token = response.json()["tenant"]["token"]

    # Send 31 requests quickly
    for _ in range(30):
        response = client.post(
            f"/in/{token}",
            json={"test": "data"},
            headers={"Stripe-Signature": "test_sig"},
        )
        assert response.status_code in [
            400,
            404,
        ]  # Expected due to missing Stripe config

    # The 31st request should be rate limited
    response = client.post(
        f"/in/{token}",
        json={"test": "data"},
        headers={"Stripe-Signature": "test_sig"},
    )
    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}


def test_payload_too_big(client):
    # Create a test tenant
    response = client.post(
        "/signup",
        json={"name": "Test Tenant", "email": "test@example.com"},
    )
    assert response.status_code == 200
    token = response.json()["tenant"]["token"]

    # Create a payload larger than 1 MiB
    large_payload = {"data": "x" * (1024 * 1024 + 1)}

    # Send the request
    response = client.post(
        f"/in/{token}",
        json=large_payload,
        headers={"Stripe-Signature": "test_sig"},
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "Payload too large"}
