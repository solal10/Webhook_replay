# Webhook Replay Service

A service for receiving, storing, and replaying webhooks with support for Stripe integration.

## Features

- Webhook ingestion and storage
- Event replay functionality
- Stripe webhook signature verification
- S3 payload storage
- Retry mechanism with exponential backoff
- API key authentication

## Onboarding / Setup

1. Clone the repository
2. Install dependencies:
   - Backend: `cd backend && poetry install`
   - Frontend: `cd frontend && npm install`
3. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```
4. Copy and configure your environment variables (see below)

## Supported Payment Service Providers

- **Stripe** is the only PSP supported in v1.

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker and Docker Compose
- PostgreSQL 15
- Redis 7
- LocalStack (for S3 emulation)

## Environment Variables

Create a `.env` file in the backend directory:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/webhooks

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS/LocalStack
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_ENDPOINT_URL=http://localhost:4566
EVENTS_BUCKET=events-dev

# Stripe
STRIPE_SIGNING_SECRET=whsec_test_123

# Security
API_KEY_SALT=test_salt

# Frontend
FRONTEND_URL=http://localhost:3000
```

## Secret Management

- **Local development:**
  - Use a `.env` file (never commit real secrets).
  - Example: `cp .env.example .env` and fill in your own values.
- **Production:**
  - Use AWS Secrets Manager to store secrets securely.
  - Inject secrets at runtime using the AWS CLI:
    ```bash
    aws secretsmanager get-secret-value --secret-id <your-secret-id> --query SecretString --output text > .env
    ```
- **CI/CD:**
  - Use GitHub Actions secrets for all sensitive values.
  - Reference them in your workflow as environment variables.

**Never commit real credentials to the repository.**

## Running the Services

### Option 1: Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Option 2: Running Locally

You need three terminals:

1. **Backend API:**
   ```bash
   cd backend
   poetry install
   poetry run uvicorn app.main:app --reload
   ```

2. **Celery Worker:**
   ```bash
   cd backend
   poetry run celery -A app.celery_app worker -Q deliveries --loglevel=info
   ```

3. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## How to Call the API

### Health Checks
- Backend: `GET http://localhost:8000/health` → `{ "status": "ok" }`
- Frontend: `GET http://localhost:3000/api/health` → `{ "status": "ok" }`

### API Documentation
- OpenAPI docs: Visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation

### Key Endpoints
- **Signup:** `POST /signup` - Create a new tenant
- **Who Am I:** `GET /me` - Get current tenant info
- **Create Target:** `POST /targets` - Set webhook target URL
- **Replay Event:** `POST /events/{event_id}/replay` - Replay a stored event
- **Ingest Webhook:** `POST /in/{token}` - Receive webhooks

## S3 Bucket & LocalStack

- The app uses a single S3 bucket, configured via the `EVENTS_BUCKET` environment variable
- LocalStack is used for local S3 emulation
- The Docker Compose setup waits for LocalStack to be healthy before starting the API and worker

## Development

- Pre-commit hooks are configured for code formatting and migration checks
- Run `pre-commit install` to set up git hooks
- Run `pre-commit run --all-files` to check all files

## Rate Limiting

The API implements rate limiting to protect against abuse:

- Global rate limit: 100 requests per 60 seconds per IP address
- Per-tenant rate limit: 30 requests per 60 seconds per tenant
- Maximum payload size: 1 MiB (1,048,576 bytes)

Rate limit responses will return a 429 status code with the following JSON:
```json
{
    "detail": "Rate limit exceeded"
}
```

Payload size limit responses will return a 413 status code with the following JSON:
```json
{
    "detail": "Payload too large"
}
```

## Configuration

The service requires Redis for rate limiting. Configure the Redis connection using the `REDIS_URL` environment variable:

```bash
REDIS_URL=redis://localhost:6379/2
```
