import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv(
            "ENV_FILE", str(Path(__file__).parent.parent.parent.parent / ".env")
        ),
        env_file_encoding="utf-8",
        extra="ignore",  # Allow extra fields in env file
    )

    database_url: str
    stripe_signing_secret: str
    aws_region: str
    s3_bucket: str
    api_key_salt: str
    frontend_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
