import os
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
    redis_url: str = "redis://webhook-redis:6379/2"
    allowed_origins: str = (
        "http://localhost:3000,https://app.example.com"  # Default allowed origins
    )
    db_encryption_kms_key: str = ""  # KMS key for database encryption

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use S3_BUCKET if EVENTS_BUCKET is not set
        if not self.events_bucket and self.s3_bucket:
            self.events_bucket = self.s3_bucket

    model_config = {"env_file": ".env", "extra": "ignore"}

    # S3 Storage Settings
    EVENTS_BUCKET: str = os.getenv("EVENTS_BUCKET", "events-dev")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_SSE_KMS_KEY_ID: str = os.getenv("AWS_SSE_KMS_KEY_ID", "")
