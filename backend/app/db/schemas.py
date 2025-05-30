from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class TenantCreate(BaseModel):
    name: str


class StripeSecretUpdate(BaseModel):
    signing_secret: str


class TenantOut(BaseModel):
    id: int
    name: str
    token: str
    stripe_signing_secret: str | None = None

    class Config:
        orm_mode = True


class TargetCreate(BaseModel):
    url: HttpUrl
    provider: str | None = None
    headers: dict | None = None


class TargetOut(TargetCreate):
    id: int

    class Config:
        orm_mode = True


class EventOut(BaseModel):
    id: int
    provider: str
    event_type: str
    duplicate: bool
    created_at: datetime

    class Config:
        orm_mode = True


class EventReplayResponse(BaseModel):
    status: str
    event_id: int
