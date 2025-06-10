import hashlib
import hmac
import json
import time
import sys
from pydantic import BaseModel
from typing import Optional


class WebhookPayload(BaseModel):
    id: str
    event: str
    data: Optional[dict] = None


def generate_stripe_signature(
    payload: dict, secret: str, timestamp: int = None
) -> tuple[str, str]:
    if timestamp is None:
        timestamp = int(time.time())
    timestamp_str = str(timestamp)
    # Use Pydantic model for consistent serialization
    payload_model = WebhookPayload(**payload)
    payload_str = payload_model.model_dump_json()
    signed_payload = f"{timestamp_str}.{payload_str}".encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()
    header = f"t={timestamp_str},v1={signature}"
    return header, payload_str


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sign.py <payload_json> <secret>")
        sys.exit(1)

    payload = json.loads(sys.argv[1])
    secret = sys.argv[2]

    header, payload_str = generate_stripe_signature(payload, secret)
    print(header)
