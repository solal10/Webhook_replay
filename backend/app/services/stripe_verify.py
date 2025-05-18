import hashlib
import hmac
import time
from typing import Optional


class StripeSignatureError(Exception):
    pass


def verify(raw_body: bytes, header: str, secret: str, tolerance: int = 300) -> None:
    """
    Raise StripeSignatureError if signature invalid.
    """
    try:
        parts = dict(kv.split("=", 1) for kv in header.split(","))
        timestamp = int(parts["t"])
        signature = parts["v1"]
    except Exception:
        raise StripeSignatureError("Malformed Stripe-Signature header")

    if abs(time.time() - timestamp) > tolerance:
        raise StripeSignatureError("Timestamp outside tolerance")

    payload = f"{timestamp}.{raw_body.decode()}".encode()
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise StripeSignatureError("Invalid signature")
