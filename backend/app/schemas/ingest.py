from typing import Any
from pydantic import BaseModel, Field


class WebhookPayload(BaseModel, extra="forbid"):
    id: str = Field(..., description="Provider event ID")
    event: str = Field(..., description="Event type / name")
    data: dict[str, Any] | None = None
