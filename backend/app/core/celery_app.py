"""Celery application — background jobs that call the exact same service
methods the sync API endpoints use (see infrastructure/tasks/), so there's
no logic duplicated between the sync and async paths.

Periodic scheduling (celery beat, Milestone E): a `celery_beat` process
(docker-compose.yml) reads `beat_schedule` below and enqueues these same
tasks on a timer — no separate scheduling logic, just the on-demand tasks
Milestone C already wrote, triggered automatically instead of by hand.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

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
    beat_schedule={
        # Nightly, before the network-optimization run below, so
        # optimization sees same-day-fresh forecasts.
        "refresh-all-forecasts-nightly": {
            "task": "forecast.refresh_all",
            "schedule": crontab(hour=2, minute=0),
        },
        # A few hours later — spans the whole network per run (one
        # medicine at a time is Milestone C's manual/API path).
        "run-network-optimization-daily": {
            "task": "optimization.run_network",
            "schedule": crontab(hour=4, minute=0),
        },
    },
)
