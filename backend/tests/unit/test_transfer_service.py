"""Unit tests for TransferService — the propose/approve/complete/cancel flow."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.transfers.service import TransferService
from app.domain.hospitals.entities import Hospital
from app.domain.shared.enums import HospitalType, TransferStatus
from app.domain.transfers.exceptions import (
    InsufficientAvailableStockError,
    InvalidTransferStateError,
    SameHospitalTransferError,
)
from tests.unit.fakes import (
    FakeHospitalRepository,
    FakeInventoryRepository,
    FakeTransferRepository,
    make_inventory_batch,
)


def _make_hospital(*, lat: float, lon: float) -> Hospital:
    return Hospital(
        id=uuid.uuid4(),
        name="Test Hospital",
        code=f"TH-{uuid.uuid4().hex[:6]}",
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
def transfer_repo() -> FakeTransferRepository:
    return FakeTransferRepository()


@pytest.fixture
def service(
    transfer_repo: FakeTransferRepository,
    inventory_repo: FakeInventoryRepository,
    hospital_repo: FakeHospitalRepository,
) -> TransferService:
    return TransferService(transfer_repo, inventory_repo, hospital_repo)


async def test_propose_rejects_same_source_and_destination(service: TransferService) -> None:
    hospital_id = uuid.uuid4()
    with pytest.raises(SameHospitalTransferError):
        await service.propose(
            source_hospital_id=hospital_id,
            destination_hospital_id=hospital_id,
            medicine_id=uuid.uuid4(),
            quantity=10,
        )


async def test_propose_rejects_insufficient_available_stock(
    service: TransferService,
    inventory_repo: FakeInventoryRepository,
    hospital_repo: FakeHospitalRepository,
) -> None:
    source = await hospital_repo.create(_make_hospital(lat=24.7, lon=46.7))
    destination = await hospital_repo.create(_make_hospital(lat=21.5, lon=39.2))
    medicine_id = uuid.uuid4()
    await inventory_repo.create(
        make_inventory_batch(
            hospital_id=source.id, medicine_id=medicine_id, current_stock=15, safety_stock=10
        )
    )  # only 5 available

    with pytest.raises(InsufficientAvailableStockError):
        await service.propose(
            source_hospital_id=source.id,
            destination_hospital_id=destination.id,
            medicine_id=medicine_id,
            quantity=10,
        )


async def test_full_transfer_lifecycle_moves_stock_between_hospitals(
    service: TransferService,
    inventory_repo: FakeInventoryRepository,
    hospital_repo: FakeHospitalRepository,
) -> None:
    source = await hospital_repo.create(_make_hospital(lat=24.7136, lon=46.6753))  # Riyadh
    destination = await hospital_repo.create(_make_hospital(lat=21.4858, lon=39.1925))  # Jeddah
    medicine_id = uuid.uuid4()
    source_batch = await inventory_repo.create(
        make_inventory_batch(
            hospital_id=source.id,
            medicine_id=medicine_id,
            current_stock=100,
            safety_stock=10,
            unit_cost_at_receipt=4.0,
        )
    )

    transfer = await service.propose(
        source_hospital_id=source.id,
        destination_hospital_id=destination.id,
        medicine_id=medicine_id,
        quantity=50,
    )
    assert transfer.status == TransferStatus.PROPOSED
    assert transfer.distance_km is not None and transfer.distance_km > 0
    assert transfer.transportation_cost is not None and transfer.transportation_cost > 0

    approved = await service.approve(transfer.id)
    assert approved.status == TransferStatus.APPROVED

    completed = await service.complete(transfer.id)
    assert completed.status == TransferStatus.COMPLETED
    assert completed.completed_at is not None

    # Stock actually moved.
    updated_source_batch = await inventory_repo.get_by_id(source_batch.id)
    assert updated_source_batch is not None
    assert updated_source_batch.current_stock == 50

    destination_batches = await inventory_repo.list_batches(
        hospital_id=destination.id, medicine_id=medicine_id
    )
    assert sum(b.current_stock for b in destination_batches) == 50


async def test_cannot_approve_a_transfer_twice(
    service: TransferService,
    inventory_repo: FakeInventoryRepository,
    hospital_repo: FakeHospitalRepository,
) -> None:
    source = await hospital_repo.create(_make_hospital(lat=24.7, lon=46.7))
    destination = await hospital_repo.create(_make_hospital(lat=21.5, lon=39.2))
    medicine_id = uuid.uuid4()
    await inventory_repo.create(
        make_inventory_batch(
            hospital_id=source.id, medicine_id=medicine_id, current_stock=100, safety_stock=0
        )
    )

    transfer = await service.propose(
        source_hospital_id=source.id,
        destination_hospital_id=destination.id,
        medicine_id=medicine_id,
        quantity=10,
    )
    await service.approve(transfer.id)

    with pytest.raises(InvalidTransferStateError):
        await service.approve(transfer.id)


async def test_cancel_from_proposed_succeeds(
    service: TransferService,
    inventory_repo: FakeInventoryRepository,
    hospital_repo: FakeHospitalRepository,
) -> None:
    source = await hospital_repo.create(_make_hospital(lat=24.7, lon=46.7))
    destination = await hospital_repo.create(_make_hospital(lat=21.5, lon=39.2))
    medicine_id = uuid.uuid4()
    await inventory_repo.create(
        make_inventory_batch(
            hospital_id=source.id, medicine_id=medicine_id, current_stock=100, safety_stock=0
        )
    )

    transfer = await service.propose(
        source_hospital_id=source.id,
        destination_hospital_id=destination.id,
        medicine_id=medicine_id,
        quantity=10,
    )
    cancelled = await service.cancel(transfer.id)
    assert cancelled.status == TransferStatus.CANCELLED
