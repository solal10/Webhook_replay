from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class TenantCreate(BaseModel):
    name: str


class TenantOut(BaseModel):
    id: int
    name: str
    token: str

    class Config:
        orm_mode = True


class ApiKeyOut(BaseModel):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class TargetCreate(BaseModel):
    url: HttpUrl
    provider: str = "stripe"


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


class DeliveryOut(BaseModel):
    id: int
    status: str
    attempt: int
    code: Optional[int]
    logged_at: datetime

    class Config:
        orm_mode = True
