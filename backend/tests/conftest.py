import os
from pathlib import Path
from unittest.mock import patch
from typing import Iterator

import boto3
import pytest
from celery import Task
from fastapi.testclient import TestClient
from moto import mock_aws
from passlib.hash import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
import redis.asyncio as aioredis
from fastapi_limiter import FastAPILimiter
import asyncio
import logging
import fakeredis.aioredis
import time
from fastapi import Depends, HTTPException
import secrets

# Set test environment variables
test_db_url = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/webhooks_test"
)
os.environ.update(
    {
        "DATABASE_URL": test_db_url,
        "STRIPE_SIGNING_SECRET": "whsec_test",
        "AWS_REGION": "us-east-1",
        "EVENTS_BUCKET": "events-dev",
        "API_KEY_SALT": "test_salt",
        "FRONTEND_URL": "http://localhost:3000",
        "REDIS_URL": "redis://localhost:6379/2",  # Use a separate Redis DB for testing
    }
)

from app.core.config import Settings, get_settings

# Import app modules after setting environment variables
from app.db import models
from app.db.models import Base
from app.db.session import SessionLocal, engine
from app.main import app

logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def celery_task_always_eager():
    with patch.object(Task, "apply_async") as mock:

        class MockAsyncResult:
            def __init__(self):
                self.id = "mock-task-id"

        mock.return_value = MockAsyncResult()
        yield mock


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(os.environ["DATABASE_URL"])
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def db(db_engine) -> Iterator[Session]:
    logger.info("Starting database transaction")
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    logger.info(f"Created test session with ID {id(session)}")

    yield session

    logger.info("Rolling back transaction")
    session.close()
    transaction.rollback()
    connection.close()
    logger.info("Transaction cleanup complete")


@pytest.fixture
def test_tenant(db: Session) -> models.Tenant:
    logger.info("Creating test tenant...")
    # Generate a unique token
    token = secrets.token_urlsafe(8)
    tenant = models.Tenant(
        name="TestTenant", token=token, stripe_signing_secret="whsec_test"
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Verify tenant exists
    found = db.query(models.Tenant).filter_by(token=token).first()
    logger.info(
        f"Created tenant with ID {tenant.id}, verified in DB: {found is not None}"
    )
    # Create API key
    api_key = models.ApiKey(tenant_id=tenant.id, hashed_key=bcrypt.hash("test_key"))
    db.add(api_key)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture(autouse=True)
def setup_database(db_engine):
    logger.info("Setting up database...")
    try:
        # Drop all tables first to ensure clean state
        Base.metadata.drop_all(db_engine)
        # Create all tables
        Base.metadata.create_all(db_engine)
        # Log table constraints before creation
        for table in Base.metadata.tables.values():
            logger.info(f"Table {table.name} constraints:")
            for const in table.constraints:
                logger.info(f"  - {const}")
        logger.info("Database setup complete")
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise
    yield
    logger.info("Tearing down database...")
    try:
        Base.metadata.drop_all(db_engine)
        logger.info("Database teardown complete")
    except Exception as e:
        logger.error(f"Error tearing down database: {e}")
        raise


@pytest.fixture
def mock_aws_s3():
    with mock_aws():
        s3 = boto3.client("s3", region_name=get_settings().aws_region)
        s3.create_bucket(Bucket=get_settings().events_bucket)
        yield s3


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def app():
    from app.main import app

    return app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def redis_client():
    """Create a fake Redis client for testing."""
    logger.info("Creating fake Redis client...")
    client = await fakeredis.aioredis.create_redis_pool()
    logger.info("Fake Redis client created successfully")
    yield client
    logger.info("Closing fake Redis client...")
    client.close()
    await client.wait_closed()
    logger.info("Fake Redis client closed")


@pytest.fixture(scope="session")
def db():
    """Create a test database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class MockRateLimiter:
    def __init__(self, times: int, seconds: int):
        self.times = times
        self.seconds = seconds
        self.requests = []
        logger.info(
            f"Initialized MockRateLimiter with times={times}, seconds={seconds}"
        )

    def __call__(self):
        now = time.time()
        # Remove old requests
        self.requests = [
            req_time for req_time in self.requests if now - req_time < self.seconds
        ]
        logger.info(f"Current request count: {len(self.requests)}/{self.times}")

        if len(self.requests) >= self.times:
            logger.info("Rate limit exceeded")
            raise HTTPException(status_code=429, detail="Too many requests")

        self.requests.append(now)
        logger.info(f"Request allowed, new count: {len(self.requests)}/{self.times}")
        return self


@pytest.fixture(scope="session")
def client(db):
    """Create a test client with a test database."""
    from app.main import app, db_session
    from fastapi_limiter.depends import RateLimiter

    app.dependency_overrides[db_session] = lambda: db

    # Override rate limiter with mock
    mock_limiter = MockRateLimiter(times=30, seconds=60)
    app.dependency_overrides[RateLimiter] = lambda: mock_limiter
    logger.info("Rate limiter dependency overridden with mock")

    with TestClient(app) as test_client:
        logger.info("Test client created")
        yield test_client
    app.dependency_overrides.clear()
    logger.info("Test client closed")
