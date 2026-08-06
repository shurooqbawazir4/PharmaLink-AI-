"""Unit tests for OptimizationService — no DB, no Docker, no real OR-Tools
training data needed (the solver itself is real; only the surrounding
repositories are fakes)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.forecast.service import ForecastService
from app.application.notifications.service import NotificationService
from app.application.optimization.service import OptimizationService
from app.application.transfers.service import TransferService
from app.domain.hospitals.entities import Hospital
from app.domain.shared.enums import HospitalType, RecommendedBy
from app.infrastructure.external.ml_client import MLForecastClient
from tests.unit.fakes import (
    FakeAlertRepository,
    FakeForecastRepository,
    FakeHospitalRepository,
    FakeInventoryRepository,
    FakeTransferRepository,
    make_inventory_batch,
)


def _make_hospital(*, lat: float, lon: float) -> Hospital:
    return Hospital(
        id=uuid.uuid4(),
        name="Hospital",
        code=f"H-{uuid.uuid4().hex[:6]}",
        latitude=lat,
        longitude=lon,
        city="City",
        region="Region",
        bed_capacity=100,
        occupancy_rate=0.5,
        type=HospitalType.GENERAL,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def hospital_repo() -> FakeHospitalRepository:
    return FakeHospitalRepository()


@pytest.fixture
def inventory_repo() -> FakeInventoryRepository:
    return FakeInventoryRepository()


@pytest.fixture
def notification_service() -> NotificationService:
    return NotificationService(FakeAlertRepository())


@pytest.fixture
def forecast_service() -> ForecastService:
    # Empty repo -> get_latest always returns None -> OptimizationService
    # falls back to InventoryRepository.average_daily_consumption (0.0 for
    # a fake with no recorded history), which is exactly what these tests
    # want: projected position reduces to current_stock - safety_stock.
    return ForecastService(FakeForecastRepository(), MLForecastClient())


@pytest.fixture
def transfer_service(
    inventory_repo: FakeInventoryRepository, hospital_repo: FakeHospitalRepository
) -> TransferService:
    return TransferService(FakeTransferRepository(), inventory_repo, hospital_repo)


@pytest.fixture
def service(
    inventory_repo: FakeInventoryRepository,
    hospital_repo: FakeHospitalRepository,
    forecast_service: ForecastService,
    transfer_service: TransferService,
    notification_service: NotificationService,
) -> OptimizationService:
    return OptimizationService(
        inventory_repo, hospital_repo, forecast_service, transfer_service, notification_service
    )


async def test_optimize_network_proposes_transfer_from_surplus_to_deficit(
    service: OptimizationService,
    hospital_repo: FakeHospitalRepository,
    inventory_repo: FakeInventoryRepository,
    notification_service: NotificationService,
) -> None:
    medicine_id = uuid.uuid4()
    surplus_hospital = await hospital_repo.create(_make_hospital(lat=24.7136, lon=46.6753))
    deficit_hospital = await hospital_repo.create(_make_hospital(lat=21.4858, lon=39.1925))

    await inventory_repo.create(
        make_inventory_batch(
            hospital_id=surplus_hospital.id,
            medicine_id=medicine_id,
            current_stock=200,
            safety_stock=20,
        )
    )
    await inventory_repo.create(
        make_inventory_batch(
            hospital_id=deficit_hospital.id,
            medicine_id=medicine_id,
            current_stock=10,
            safety_stock=20,
        )
    )

    transfers = await service.optimize_network(medicine_id)

    assert len(transfers) == 1
    transfer = transfers[0]
    assert transfer.source_hospital_id == surplus_hospital.id
    assert transfer.destination_hospital_id == deficit_hospital.id
    assert transfer.recommended_by == RecommendedBy.AI
    assert transfer.quantity > 0

    alerts = await notification_service.list(hospital_id=deficit_hospital.id)
    assert len(alerts) == 1
    assert alerts[0].type.value == "transfer_suggested"


async def test_optimize_network_returns_empty_when_no_hospital_is_in_deficit(
    service: OptimizationService,
    hospital_repo: FakeHospitalRepository,
    inventory_repo: FakeInventoryRepository,
) -> None:
    medicine_id = uuid.uuid4()
    hospital = await hospital_repo.create(_make_hospital(lat=24.7136, lon=46.6753))
    await inventory_repo.create(
        make_inventory_batch(
            hospital_id=hospital.id, medicine_id=medicine_id, current_stock=100, safety_stock=20
        )
    )

    transfers = await service.optimize_network(medicine_id)

    assert transfers == []


async def test_optimize_network_ignores_hospitals_with_no_batches_for_the_medicine(
    service: OptimizationService, hospital_repo: FakeHospitalRepository
) -> None:
    medicine_id = uuid.uuid4()
    await hospital_repo.create(_make_hospital(lat=24.7136, lon=46.6753))
    await hospital_repo.create(_make_hospital(lat=21.4858, lon=39.1925))

    transfers = await service.optimize_network(medicine_id)

    assert transfers == []
