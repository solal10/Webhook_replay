import os
from pathlib import Path

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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

# Import app modules after setting environment variables
from app.db import models
from app.db.models import Base
from app.db.session import SessionLocal
from app.main import app


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(os.environ["DATABASE_URL"])
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine) -> Session:
    import logging

    logger = logging.getLogger(__name__)

    logger.info("Starting database transaction")
    connection = engine.connect()
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
    import logging

    logger = logging.getLogger(__name__)

    logger.info("Creating test tenant...")
    tenant = models.Tenant(
        name="TestTenant", token="abc123", stripe_signing_secret="whsec_test"
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Verify tenant exists
    found = db.query(models.Tenant).filter_by(token="abc123").first()
    logger.info(
        f"Created tenant with ID {tenant.id}, verified in DB: {found is not None}"
    )
    return tenant


@pytest.fixture(autouse=True)
def setup_database(engine):
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Setting up database...")
    try:
        # Log table constraints before creation
        for table in Base.metadata.tables.values():
            logger.info(f"Table {table.name} constraints:")
            for const in table.constraints:
                logger.info(f"  - {const}")

        Base.metadata.create_all(engine)
        logger.info("Database setup complete")
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise
    yield
    logger.info("Tearing down database...")
    try:
        Base.metadata.drop_all(engine)
        logger.info("Database teardown complete")
    except Exception as e:
        logger.error(f"Error tearing down database: {e}")
        raise


@pytest.fixture(autouse=True)
def mock_aws_s3():
    """Mock AWS services for testing"""
    with mock_aws():
        s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
        s3.create_bucket(Bucket=os.environ["S3_BUCKET"])
        yield s3


@pytest.fixture
def settings():
    from app.core.config import Settings

    # Force reload settings from test environment
    settings = Settings(_env_file=None)
    return settings


@pytest.fixture
def app():
    from app.main import app

    return app


@pytest.fixture
def client(app, db, settings) -> TestClient:
    from app.core.config import get_settings
    from app.main import db_session

    # Override settings
    def get_test_settings():
        return settings

    # Override database session
    def get_test_db():
        # Create a new session with the same connection
        test_session = Session(bind=db.connection())
        try:
            yield test_session
        finally:
            test_session.close()

    app.dependency_overrides[get_settings] = get_test_settings
    app.dependency_overrides[db_session] = get_test_db
    yield TestClient(app)
    app.dependency_overrides.clear()
