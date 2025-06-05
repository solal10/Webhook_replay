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
