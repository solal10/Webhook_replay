# Security

## Rate Limiting & Body-Size

The API implements several rate-limiting and size restrictions to protect against abuse:

### Global Rate Limits
- 100 requests per minute per IP address
- Configurable via environment variable: `RATE_LIMIT_GLOBAL_TIMES` and `RATE_LIMIT_GLOBAL_SECONDS`

### Per-Tenant Rate Limits
- 30 requests per minute per tenant token on `/in/{token}` endpoint
- Configurable via environment variable: `RATE_LIMIT_TENANT_TIMES` and `RATE_LIMIT_TENANT_SECONDS`

### Body Size Limits
- Maximum request body size: 1 MiB (1,048,576 bytes)
- Requests exceeding this limit will receive a 413 Payload Too Large response
- Configurable via environment variable: `MAX_BODY_SIZE_BYTES`

### Redis Configuration
- Rate limiting uses Redis for state management
- Redis URL configurable via environment variable: `REDIS_URL`
- Default: `redis://localhost:6379/2`

## Secure HTTP Headers & CORS

The API sets the following security headers on all responses:

| Header                        | Value                                                                 |
|-------------------------------|-----------------------------------------------------------------------|
| Strict-Transport-Security     | max-age=63072000; includeSubDomains; preload                          |
| X-Frame-Options               | DENY                                                                  |
| X-Content-Type-Options        | nosniff                                                               |
| X-XSS-Protection              | 1; mode=block                                                         |
| Referrer-Policy               | no-referrer                                                           |
| Content-Security-Policy       | default-src 'self'; frame-ancestors 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' |

Example:

```bash
$ curl -I http://localhost:8000/health
HTTP/1.1 200 OK
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: no-referrer
Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
```

### CORS

Allowed origins are set via the `ALLOWED_ORIGINS` environment variable (comma-separated list).

To change allowed origins, set `ALLOWED_ORIGINS` in your environment or `.env` file.

Example preflight request:

```bash
$ curl -X OPTIONS -H "Origin: https://app.example.com" -H "Access-Control-Request-Method: POST" http://localhost:8000/in/test
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://app.example.com
... (other CORS headers)
```

## Input Validation

The `/in/{token}` endpoint validates incoming webhook payloads using a strict schema:

```json
{
  "id": "evt_123",      // Required: Provider event ID
  "event": "payment",   // Required: Event type/name
  "data": {            // Optional: Event data
    "amount": 1000,
    "currency": "usd"
  }
}
```

Validation rules:
- Empty payloads are rejected (400 Bad Request)
- Unknown fields are rejected (400 Bad Request)
- Missing required fields return 400 with specific error messages
- All payloads must be valid JSON

Example error responses:
```json
// Missing required field
{
  "detail": "id field required"
}

// Unknown field
{
  "detail": "extra fields not permitted"
}

// Empty payload
{
  "detail": "Empty JSON body"
}
```

# Security Documentation

## S3 Storage Security

### Bucket Configuration
- **Public Access Blocking**: All public access is blocked at the bucket level
  - BlockPublicAcls: true
  - IgnorePublicAcls: true
  - BlockPublicPolicy: true
  - RestrictPublicBuckets: true

### Encryption
- **Server-Side Encryption**: All objects are encrypted at rest
  - Primary: AWS KMS (when AWS_SSE_KMS_KEY_ID is configured)
  - Fallback: AES-256 (when no KMS key is configured)
- **Key Rotation**: KMS keys are rotated every 365 days
- **Bucket Key**: Enabled for reduced KMS API costs

### Access Control
- **No Public Reads**: Presigned URLs are not supported
- **IAM Policies**: Access is restricted to application IAM roles
- **Object ACLs**: Disabled in favor of bucket policies

### Best Practices
1. Never expose S3 URLs directly
2. Use IAM roles for service access
3. Monitor bucket access via CloudTrail
4. Regular security audits of bucket policies
5. Enable versioning for data protection
