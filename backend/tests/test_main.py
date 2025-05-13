import os
from pathlib import Path

from app.main import app
from fastapi.testclient import TestClient

# Set test environment variables
os.environ.update(
    {
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/webhooks_test",
        "STRIPE_SIGNING_SECRET": "whsec_test",
        "AWS_REGION": "us-east-1",
        "S3_BUCKET": "webhook-payloads-test",
        "API_KEY_SALT": "test_salt",
        "FRONTEND_URL": "http://localhost:3000",
    }
)

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "env" in data
    assert data["env"]["db"].endswith("webhooks_test")
    assert data["env"]["bucket"] == "webhook-payloads-test"
