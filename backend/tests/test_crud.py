import pytest
from app.db import crud, models, schemas
from app.db.session import SessionLocal, engine
from sqlalchemy import exc
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def setup_database():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def tenant(db: Session) -> models.Tenant:
    return crud.create_tenant(db, schemas.TenantCreate(name="Acme"))


def test_create_tenant(db: Session):
    tenant = crud.create_tenant(db, schemas.TenantCreate(name="Test Corp"))
    assert tenant.name == "Test Corp"
    assert tenant.token is not None


def test_create_tenant_unique_token(db: Session):
    tenant1 = crud.create_tenant(db, schemas.TenantCreate(name="Test Corp 1"))
    tenant2 = crud.create_tenant(db, schemas.TenantCreate(name="Test Corp 2"))
    assert tenant1.token != tenant2.token


def test_issue_api_key(db: Session, tenant: models.Tenant):
    api_key = crud.issue_api_key(db, tenant.id)
    assert api_key is not None
    assert len(api_key) > 16  # Ensure it's a reasonably long key


def test_verify_api_key(db: Session, tenant: models.Tenant):
    api_key = crud.issue_api_key(db, tenant.id)
    verified_tenant = crud.verify_api_key(db, api_key)
    assert verified_tenant.id == tenant.id
    assert verified_tenant.name == tenant.name


def test_verify_invalid_api_key(db: Session):
    assert crud.verify_api_key(db, "invalid_key") is None


def test_multiple_api_keys_per_tenant(db: Session, tenant: models.Tenant):
    key1 = crud.issue_api_key(db, tenant.id)
    key2 = crud.issue_api_key(db, tenant.id)

    assert key1 != key2
    assert crud.verify_api_key(db, key1).id == tenant.id
    assert crud.verify_api_key(db, key2).id == tenant.id
