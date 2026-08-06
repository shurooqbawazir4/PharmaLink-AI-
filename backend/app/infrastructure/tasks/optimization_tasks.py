"""Celery task: run the network-wide transfer optimizer for every active
medicine — the same `OptimizationService.optimize_network()` the sync
`POST /optimization/transfers/{medicine_id}` endpoint calls, looped across
the catalogue. Trigger manually for now (celery beat scheduling is a
Milestone E concern):

    docker compose run --rm backend celery -A app.core.celery_app call \\
        optimization.run_network
"""

from __future__ import annotations

import asyncio
import logging

from app.application.forecast.service import ForecastService
from app.application.notifications.service import NotificationService
from app.application.optimization.service import OptimizationService
from app.application.transfers.service import TransferService
from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.core.di import get_ml_forecast_client
from app.infrastructure.db.repositories.alert_repository import SQLAlchemyAlertRepository
from app.infrastructure.db.repositories.forecast_repository import SQLAlchemyForecastRepository
from app.infrastructure.db.repositories.hospital_repository import SQLAlchemyHospitalRepository
from app.infrastructure.db.repositories.inventory_repository import SQLAlchemyInventoryRepository
from app.infrastructure.db.repositories.medicine_repository import SQLAlchemyMedicineRepository
from app.infrastructure.db.repositories.transfer_repository import SQLAlchemyTransferRepository

logger = logging.getLogger(__name__)


async def _run_network_optimization() -> int:
    async with AsyncSessionLocal() as session:
        inventory_repo = SQLAlchemyInventoryRepository(session)
        hospital_repo = SQLAlchemyHospitalRepository(session)
        forecast_repo = SQLAlchemyForecastRepository(session)
        transfer_repo = SQLAlchemyTransferRepository(session)
        alert_repo = SQLAlchemyAlertRepository(session)
        medicine_repo = SQLAlchemyMedicineRepository(session)

        forecast_service = ForecastService(forecast_repo, get_ml_forecast_client())
        transfer_service = TransferService(transfer_repo, inventory_repo, hospital_repo)
        notification_service = NotificationService(alert_repo)
        optimization_service = OptimizationService(
            inventory_repo, hospital_repo, forecast_service, transfer_service, notification_service
        )

        medicines = await medicine_repo.list(is_active=True)
        total_transfers = 0
        for medicine in medicines:
            transfers = await optimization_service.optimize_network(medicine.id)
            total_transfers += len(transfers)

        await session.commit()
        return total_transfers


@celery_app.task(name="optimization.run_network")  # type: ignore[untyped-decorator]  # celery ships no stubs
def run_network_optimization() -> int:
    total_transfers = asyncio.run(_run_network_optimization())
    logger.info("run_network_optimization: proposed %d transfers", total_transfers)
    return total_transfers
