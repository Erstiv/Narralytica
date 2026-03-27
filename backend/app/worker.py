"""Celery worker for background jobs (compression monitoring, indexing, etc.)."""
from celery import Celery

celery_app = Celery(
    "narralytica",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task
def placeholder_task():
    """Placeholder. Real tasks (indexing, embedding gen) added in Phase 2."""
    return {"status": "ok"}
