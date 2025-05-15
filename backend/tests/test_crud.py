from app.db import crud, models, schemas
from app.db.session import SessionLocal


def test_tenant_api_key_roundtrip():
    db = SessionLocal()
    tenant = crud.create_tenant(db, schemas.TenantCreate(name="Acme Inc"))
    api_key_raw = crud.issue_api_key(db, tenant.id)
    fetched = crud.verify_api_key(db, api_key_raw)
    assert fetched and fetched.id == tenant.id
