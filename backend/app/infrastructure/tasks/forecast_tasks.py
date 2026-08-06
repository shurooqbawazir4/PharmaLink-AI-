"""Celery task: refresh forecasts for every (hospital, medicine) pair that
currently has inventory — the same `ForecastService.generate()` the sync
`POST /forecasts/generate/...` endpoint calls, just looped across the
whole network. Trigger manually for now (celery beat scheduling is a
Milestone E concern):

    docker compose run --rm backend celery -A app.core.celery_app call \\
        forecast.refresh_all
"""

from __future__ import annotations

import asyncio
import logging

from app.application.forecast.service import ForecastService
from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.di import get_ml_forecast_client
from app.infrastructure.db.repositories.forecast_repository import SQLAlchemyForecastRepository
from app.infrastructure.db.repositories.inventory_repository import SQLAlchemyInventoryRepository

logger = logging.getLogger(__name__)

_DEFAULT_HORIZON_DAYS = 30


async def _refresh_all_forecasts() -> int:
    async with AsyncSessionLocal() as session:
        inventory_repo = SQLAlchemyInventoryRepository(session)
        forecast_repo = SQLAlchemyForecastRepository(session)
        forecast_service = ForecastService(forecast_repo, get_ml_forecast_client())

        batches = await inventory_repo.list_batches()
        pairs = {(batch.hospital_id, batch.medicine_id) for batch in batches}

        generated = 0
        for hospital_id, medicine_id in pairs:
            await forecast_service.generate(hospital_id, medicine_id, _DEFAULT_HORIZON_DAYS)
            generated += 1

        await session.commit()
        return generated


@celery_app.task(name="forecast.refresh_all")  # type: ignore[untyped-decorator]  # celery ships no stubs
def refresh_all_forecasts() -> int:
    generated = asyncio.run(_refresh_all_forecasts())
    logger.info("refresh_all_forecasts: generated %d forecasts", generated)
    return generated
