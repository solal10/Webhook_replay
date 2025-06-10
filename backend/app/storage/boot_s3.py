import boto3
import json
from botocore.exceptions import ClientError
from app.core.settings import Settings
import os

settings = Settings()


def ensure_secure_bucket():
    """Ensure the S3 bucket exists and is configured with security best practices."""
    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        endpoint_url=os.getenv("AWS_ENDPOINT_URL"),
    )
    try:
        s3.head_bucket(Bucket=settings.EVENTS_BUCKET)
    except ClientError:
        create_kwargs = {"Bucket": settings.EVENTS_BUCKET}
        if settings.AWS_REGION != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {
                "LocationConstraint": settings.AWS_REGION
            }
        s3.create_bucket(**create_kwargs)

    # Block Public Access
    s3.put_public_access_block(
        Bucket=settings.EVENTS_BUCKET,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )

    # Default encryption (SSE-KMS or AES256)
    enc_cfg = {
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": (
                        "aws:kms" if settings.AWS_SSE_KMS_KEY_ID else "AES256"
                    ),
                    **(
                        {"KMSMasterKeyID": settings.AWS_SSE_KMS_KEY_ID}
                        if settings.AWS_SSE_KMS_KEY_ID
                        else {}
                    ),
                },
                "BucketKeyEnabled": True,
            }
        ]
    }
    s3.put_bucket_encryption(
        Bucket=settings.EVENTS_BUCKET, ServerSideEncryptionConfiguration=enc_cfg
    )
