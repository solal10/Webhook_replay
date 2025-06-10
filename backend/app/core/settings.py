import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/2"
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

    # S3 Storage Settings
    EVENTS_BUCKET: str = os.getenv("EVENTS_BUCKET", "events-dev")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_SSE_KMS_KEY_ID: str = os.getenv("AWS_SSE_KMS_KEY_ID", "")
