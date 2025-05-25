FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi --no-root

COPY . .

CMD ["poetry", "run", "celery", "-A", "app.celery_app", "worker", "-Q", "deliveries", "--loglevel=info"]
