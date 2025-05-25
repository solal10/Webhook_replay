from app.core.config import get_settings
from celery import Celery

settings = get_settings()

celery = Celery(
    "app",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Import tasks
celery.conf.imports = ["app.tasks"]

# Set task routes
celery.conf.task_routes = {"app.tasks.forward_event": {"queue": "deliveries"}}
