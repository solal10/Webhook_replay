#!/usr/bin/env python
"""
Seed script — creates a demo tenant + API key.

Usage:
    poetry run python seed.py
"""
from app.db import crud, schemas
from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    tenant = crud.create_tenant(db, schemas.TenantCreate(name="Demo Corp"))
    api_key = crud.issue_api_key(db, tenant.id)
    print("=== Demo Tenant Seeded ===")
    print(f"Tenant name : {tenant.name}")
    print(f"Tenant id   : {tenant.id}")
    print(f"Ingress URL : https://hooks.local/in/{tenant.token}")
    print(f"API KEY     : {api_key}  (store this securely!)")


if __name__ == "__main__":
    main()
