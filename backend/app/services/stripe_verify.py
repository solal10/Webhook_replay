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
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"Verifying Stripe signature with header: {header}")
    logger.info(f"Raw body: {raw_body.decode()}")
    try:
        parts = dict(kv.split("=", 1) for kv in header.split(","))
        timestamp = int(parts["t"])
        signature = parts["v1"]
        logger.info(f"Received signature: {signature}")
        logger.info(f"Using secret: {secret}")
    except Exception:
        raise StripeSignatureError("Malformed Stripe-Signature header")

    if abs(time.time() - timestamp) > tolerance:
        raise StripeSignatureError("Timestamp outside tolerance")

    raw_body_str = raw_body.decode()
    logger.info(f"Raw body string: {raw_body_str}")
    logger.info(f"Raw body repr: {repr(raw_body_str)}")
    logger.info(f"Raw body bytes: {raw_body}")
    payload = f"{timestamp}.{raw_body_str}".encode("utf-8")
    logger.info(f"Payload to sign: {payload}")
    logger.info(
        f"Payload repr: {repr(f'{timestamp}.{raw_body_str}')}"
    )  # Use single quotes inside f-string
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    logger.info(f"Expected signature: {expected}")
    logger.info(f"Received signature: {signature}")
    logger.info(f"Secret used: {secret}")
    if not hmac.compare_digest(expected, signature):
        raise StripeSignatureError("Invalid signature")
