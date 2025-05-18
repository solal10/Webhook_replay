import secrets

from app.db import models, schemas
from passlib.hash import bcrypt
from sqlalchemy.orm import Session


def create_tenant(db: Session, data: schemas.TenantCreate) -> models.Tenant:
    token = secrets.token_urlsafe(16)
    tenant = models.Tenant(name=data.name, token=token)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def issue_api_key(db: Session, tenant_id: int) -> str:
    raw = secrets.token_urlsafe(24)
    hashed = bcrypt.hash(raw)
    key = models.ApiKey(tenant_id=tenant_id, hashed_key=hashed)
    db.add(key)
    db.commit()
    return raw


def verify_api_key(db: Session, raw: str):
    for ak in db.query(models.ApiKey).all():
        if bcrypt.verify(raw, ak.hashed_key):
            return ak.tenant
    return None


def upsert_target(db: Session, tenant_id: int, data: schemas.TargetCreate):
    target = (
        db.query(models.Target)
        .filter_by(tenant_id=tenant_id, provider=data.provider)
        .first()
    )
    if target:
        target.url = data.url
    else:
        target = models.Target(tenant_id=tenant_id, **data.dict())
        db.add(target)
    db.commit()
    db.refresh(target)
    return target


def list_events(db: Session, tenant_id: int, limit: int = 100):
    return (
        db.query(models.Event)
        .filter_by(tenant_id=tenant_id)
        .order_by(models.Event.created_at.desc())
        .limit(limit)
        .all()
    )
