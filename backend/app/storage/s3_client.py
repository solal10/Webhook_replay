import boto3
from app.core.settings import Settings

settings = Settings()


def get_s3_client():
    """Get a configured S3 client."""
    return boto3.client("s3", region_name=settings.AWS_REGION)


def store_event_payload(key: str, raw_body: bytes) -> None:
    """
    Store an event payload in S3 with server-side encryption.

    Args:
        key: The S3 object key
        raw_body: The raw event payload bytes
    """
    s3 = get_s3_client()
    s3.put_object(
        Bucket=settings.EVENTS_BUCKET,
        Key=key,
        Body=raw_body,
        ContentType="application/json",
        ServerSideEncryption="aws:kms" if settings.AWS_SSE_KMS_KEY_ID else "AES256",
        **(
            {"SSEKMSKeyId": settings.AWS_SSE_KMS_KEY_ID}
            if settings.AWS_SSE_KMS_KEY_ID
            else {}
        )
    )
