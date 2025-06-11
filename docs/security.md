# Security Documentation

## 1. Overview

This document outlines the security posture of our webhook replay platform. We employ a multi-layered approach to protect webhook data, API keys, and PII, ensuring confidentiality, integrity, and availability. Our security measures include edge-rate protection, strict input validation, encryption in transit and at rest, and robust CORS and security headers.

## 2. Threat Model

### Assets
- Webhook data
- API keys
- PII (Personally Identifiable Information)

### Adversaries
- Unauthenticated internet users
- Compromised tenants
- Rogue insiders

### Goals
- Confidentiality: Protect sensitive data from unauthorized access.
- Integrity: Ensure data is not altered in transit or at rest.
- Availability: Maintain service uptime and performance.

## 3. Defensive Controls

### 3.1 Edge-Rate Protection
- 100 requests per minute per IP (global)
- 30 requests per minute per tenant on `/in/{token}`
- Body size limit: 1 MiB (413 error if exceeded)

### 3.2 Security Headers
```http
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Content-Security-Policy: default-src 'self'
```

### 3.3 CORS Policy
- Allowed origins via environment variable `ALLOWED_ORIGINS`
- Credentials allowed, methods: GET, POST, PUT, DELETE

### 3.4 Input Validation
- Pydantic schema: `id`, `event`, `data`
- `extra="forbid"` blocks unknown keys

### 3.5 Storage Security
- S3 bucket: `BlockPublicAccess = true`
- Server-Side Encryption: AES-256 or AWS KMS
- No presigned downloads

## 4. Encryption in Transit
- HTTPS-only (HSTS preload)
- TLS 1.2 minimum; automatic redirects

## 5. Encryption at Rest
- Database volume encrypted (cloud-KMS)
- Field-level AES-GCM for sensitive columns (planned Phase 6.3)
- Cloud Postgres:
  - AWS RDS / Aurora: enable storage_encrypted=true and select your KMS key
  - GCP Cloud SQL: toggle "Enable Encryption" (disk encryption is default)
  - Fly.io Postgres: volumes are LUKS-encrypted by default

## 6. Rate-Limit & Size Configuration
- Tune via environment variables:
  - `GLOBAL_RPM`: Global requests per minute
  - `TENANT_RPM`: Tenant requests per minute
  - `MAX_BODY_BYTES`: Maximum body size in bytes

## 7. Future Work
- Field encryption
- Incident response playbook (Phase 14.4)
- Periodic security review cadence
