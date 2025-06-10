# RULES: How to Start and Test the Webhook Replay Service

## 1. Start All Services

```sh
docker compose up -d
```

## 2. Run Alembic Migration (if needed)

```sh
docker compose exec api alembic upgrade head
```

## 3. Create a Tenant

```sh
curl -X POST -H "Content-Type: application/json" -d '{"name":"test-tenant"}' http://localhost:8000/signup
```
- Save the `token` from the response (e.g. `hy49MzHyIi3iVTBgTniLVQ`).

## 4. Set Stripe Signing Secret

```sh
curl -X PUT -H "Content-Type: application/json" -d '{"signing_secret":"whsec_test_secret"}' http://localhost:8000/tenants/<TOKEN>/stripe
```
- Replace `<TOKEN>` with the value from the previous step.

## 5. Generate a Stripe Signature for a Test Payload

```sh
python3 backend/sign.py '{"id":"evt_1","event":"ping","data":null}' whsec_test_secret
```
- Copy the `Stripe-Signature` header from the output.

## 6. Send a Webhook Request

```sh
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Stripe-Signature: t=...v1=..." \
  -d '{"id":"evt_1","event":"ping","data":null}' \
  http://localhost:8000/in/<TOKEN>
```
- Replace the `Stripe-Signature` and `<TOKEN>` with the values from previous steps.

## 7. Validation Test Cases

### Test Case 1: Empty JSON Body
```sh
curl -X POST -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:8000/in/<TOKEN>
```
Expected: 400 Bad Request
```
{
  "detail": [
    {
      "type": "missing",
      "loc": ["id"],
      "msg": "Field required",
      "input": {},
      "url": "https://errors.pydantic.dev/2.11/v/missing"
    },
    {
      "type": "missing",
      "loc": ["event"],
      "msg": "Field required",
      "input": {},
      "url": "https://errors.pydantic.dev/2.11/v/missing"
    }
  ]
}
```

### Test Case 2: Extra Field Not Permitted
```sh
curl -X POST -H "Content-Type: application/json" \
  -d '{"id":"evt_1","event":"ping","extra":42}' \
  http://localhost:8000/in/<TOKEN>
```
Expected: 400 Bad Request
```
{
  "detail": [
    {
      "type": "extra_forbidden",
      "loc": ["extra"],
      "msg": "Extra inputs are not permitted",
      "input": 42,
      "url": "https://errors.pydantic.dev/2.11/v/extra_forbidden"
    }
  ]
}
```

### Test Case 3: Missing Data Field
```sh
curl -X POST -H "Content-Type: application/json" \
  -d '{"id":"evt_1","event":"ping"}' \
  http://localhost:8000/in/<TOKEN>
```
Expected: 400 Bad Request
```
{
  "detail": "Missing Stripe signature"
}
```

---

**If you see `{"status":"received"}` you are DONE.**

If you see a signature or timestamp error, re-run the signature generation and immediately send the request.
