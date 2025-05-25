import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    stripe_signing_secret: str
    aws_region: str
    events_bucket: str = ""
    s3_bucket: str = ""
    api_key_salt: str
    frontend_url: str
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_endpoint_url: str | None = None
    redis_url: str = "redis://localhost:6379/0"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use S3_BUCKET if EVENTS_BUCKET is not set
        if not self.events_bucket and self.s3_bucket:
            self.events_bucket = self.s3_bucket

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
