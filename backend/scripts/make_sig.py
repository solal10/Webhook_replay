#!/usr/bin/env python3

import hashlib
import hmac
import json
import sys
import time


def make_stripe_signature(secret: str, payload: str) -> str:
    """Generate a Stripe webhook signature for testing."""
    ts = int(time.time())
    payload_bytes = payload.encode("utf-8")
    payload_with_ts = f"{ts}.{payload}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), payload_with_ts, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: make_sig.py <secret> <payload>")
        sys.exit(1)

    secret = sys.argv[1]
    payload = sys.argv[2]

    # Validate payload is valid JSON
    try:
        json.loads(payload)
    except json.JSONDecodeError:
        print("Error: Payload must be valid JSON", file=sys.stderr)
        sys.exit(1)

    print(make_stripe_signature(secret, payload))
