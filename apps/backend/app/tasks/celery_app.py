from celery import Celery
from kombu import Queue

from app.core.config import settings

celery_app = Celery("evolvai", broker=settings.celery_broker, backend=settings.celery_backend)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},
    result_backend_transport_options={"visibility_timeout": 3600},
    task_default_queue="workflows",
    task_queues=(
        Queue("workflows"),
        Queue("webhooks"),
        Queue("scheduled"),
        Queue("pr"),
    ),
    imports=(
        "app.tasks.workflow_tasks",
        "app.tasks.webhook_tasks",
        "app.tasks.scheduled_tasks",
        "app.tasks.ingestion_tasks",
    ),
)
