# Webhook Replay

A modern web application for managing and replaying webhook events.

## Project Structure

- `/backend` - FastAPI server (Python 3.11)
- `/frontend` - Next.js 14 web interface (TypeScript)
- `/infra` - Infrastructure as Code
- `/docs` - Project documentation

## Development

### Backend

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
yarn install
yarn dev
```

## Testing

- Backend: `cd backend && poetry run pytest`
- Frontend: `cd frontend && yarn test`

## Code Quality

This project uses pre-commit hooks for code formatting:
- Black for Python formatting
- isort for Python import sorting

To install hooks: `pre-commit install`
