import hashlib
import hmac
import json
import time


def generate_stripe_signature(payload: dict, secret: str) -> tuple[str, str]:
    timestamp = str(int(time.time()))
    payload_str = json.dumps(payload, separators=(",", ":"))
    signed_payload = f"{timestamp}.{payload_str}".encode("utf-8")
    signature = hmac.new(
        secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()
    header = f"t={timestamp},v1={signature}"
    return header, payload_str


payload = {"test": "retry", "timestamp": int(time.time())}
header, payload_str = generate_stripe_signature(payload, "test_secret")
print(f"Stripe-Signature: {header}")
print(f"Payload dict: {payload}")
print(f"Payload str: {payload_str}")
print(f"Payload bytes: {payload_str.encode('utf-8')}")
print(f"Payload repr: {repr(payload_str)}")
