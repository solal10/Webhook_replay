import os
from pathlib import Path

import pytest
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


@pytest.fixture
def client():
    return TestClient(app)
