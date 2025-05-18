import os
from pathlib import Path

import pytest
from app.db.models import Base
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(os.environ["DATABASE_URL"])
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def setup_database(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client():
    from app.core.config import Settings, get_settings

    # Override settings for testing
    def get_test_settings() -> Settings:
        settings = get_settings()
        settings.database_url = os.environ["DATABASE_URL"]
        return settings

    app.dependency_overrides[get_settings] = get_test_settings
    yield TestClient(app)
    app.dependency_overrides.clear()
