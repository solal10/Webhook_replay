from app.core.config import get_settings
from app.db import crud, models, schemas
from app.db.session import SessionLocal
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

app = FastAPI()
bearer_scheme = HTTPBearer()


# ---------- dependency ----------
def db_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_tenant(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(db_session),
) -> models.Tenant:
    tenant = crud.verify_api_key(db, creds.credentials)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return tenant


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "settings": {
            "database_url": get_settings().database_url,
            "stripe_signing_secret": get_settings().stripe_signing_secret,
            "aws_region": get_settings().aws_region,
            "s3_bucket": get_settings().s3_bucket,
        },
    }


# ---------- signup ----------
@app.post("/signup")
def signup(data: schemas.TenantCreate, db: Session = Depends(db_session)):
    tenant = crud.create_tenant(db, data)
    api_key = crud.issue_api_key(db, tenant.id)
    return {
        "tenant": {"id": tenant.id, "name": tenant.name, "token": tenant.token},
        "api_key": api_key,
        "ingress_url": f"https://hooks.local/in/{tenant.token}",
    }


# ---------- whoami ----------
@app.get("/me")
def who_am_i(tenant: models.Tenant = Depends(current_tenant)):
    return {"id": tenant.id, "name": tenant.name, "token": tenant.token}
