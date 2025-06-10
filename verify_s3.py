import boto3
import json
import os

# Configure S3 client
s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)


def check_bucket_settings():
    bucket = "events-dev"

    # Check encryption
    print("\nChecking bucket encryption...")
    try:
        encryption = s3.get_bucket_encryption(Bucket=bucket)
        print(json.dumps(encryption, indent=2))
    except Exception as e:
        print(f"Error getting encryption: {e}")

    # Check public access block
    print("\nChecking public access block...")
    try:
        public_access = s3.get_public_access_block(Bucket=bucket)
        print(json.dumps(public_access, indent=2))
    except Exception as e:
        print(f"Error getting public access block: {e}")


if __name__ == "__main__":
    check_bucket_settings()
