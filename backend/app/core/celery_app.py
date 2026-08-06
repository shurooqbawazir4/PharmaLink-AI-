"""Celery application — background jobs that call the exact same service
methods the sync API endpoints use (see infrastructure/tasks/), so there's
no logic duplicated between the sync and async paths.

Periodic scheduling (celery beat) is deferred to Milestone E's full
integration pass — this milestone wires up a working worker + on-demand
tasks, not a production cron schedule.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "medcycle",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.infrastructure.tasks.forecast_tasks",
        "app.infrastructure.tasks.optimization_tasks",
    ],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
