from app.db import crud, schemas
from app.db.session import SessionLocal


def test_tenant_roundtrip():
    db = SessionLocal()
    tenant = crud.create_tenant(db, schemas.TenantCreate(name="Acme"))
    api_key = crud.issue_api_key(db, tenant.id)
    assert crud.verify_api_key(db, api_key).id == tenant.id
