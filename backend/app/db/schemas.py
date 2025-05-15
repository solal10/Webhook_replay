from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, HttpUrl


class TenantCreate(BaseModel):
    name: str


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    token: str


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class TargetCreate(BaseModel):
    url: HttpUrl
    provider: str = "stripe"


class TargetOut(TargetCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    event_type: str
    duplicate: bool
    created_at: datetime


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    attempt: int
    code: Optional[int]
    logged_at: datetime
