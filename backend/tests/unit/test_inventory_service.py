"""Unit tests for InventoryService business rules — no DB, no Docker."""

from __future__ import annotations

import uuid

import pytest

from app.application.inventory.service import InventoryService
from app.application.notifications.service import NotificationService
from app.domain.inventory.exceptions import InsufficientStockError, InventoryBatchNotFoundError
from app.domain.shared.enums import InventoryChangeReason
from tests.unit.fakes import FakeAlertRepository, FakeInventoryRepository, make_inventory_batch


@pytest.fixture
def repo() -> FakeInventoryRepository:
    return FakeInventoryRepository()


@pytest.fixture
def service(repo: FakeInventoryRepository) -> InventoryService:
    return InventoryService(repo)


async def test_receive_stock_creates_a_batch_at_the_given_quantity(
    service: InventoryService,
) -> None:
    hospital_id, medicine_id = uuid.uuid4(), uuid.uuid4()
    batch = await service.receive_stock(
        hospital_id=hospital_id,
        medicine_id=medicine_id,
        batch_number="B-1",
        quantity=100,
        expiry_date=make_inventory_batch().expiry_date,
        unit_cost_at_receipt=2.5,
        safety_stock=20,
    )
    assert batch.current_stock == 100
    assert batch.hospital_id == hospital_id
    assert batch.medicine_id == medicine_id


async def test_consume_reduces_stock_and_records_history(
    service: InventoryService, repo: FakeInventoryRepository
) -> None:
    batch = make_inventory_batch(current_stock=50, safety_stock=10)
    await repo.create(batch)

    change = await service.consume(batch.id, 20)

    assert change.batch.current_stock == 30
    assert change.reason == InventoryChangeReason.CONSUMPTION


async def test_consume_more_than_available_raises_insufficient_stock(
    service: InventoryService, repo: FakeInventoryRepository
) -> None:
    batch = make_inventory_batch(current_stock=5, safety_stock=0)
    await repo.create(batch)

    with pytest.raises(InsufficientStockError):
        await service.consume(batch.id, 10)


async def test_consume_missing_batch_raises_not_found(service: InventoryService) -> None:
    with pytest.raises(InventoryBatchNotFoundError):
        await service.consume(uuid.uuid4(), 1)


async def test_consume_below_safety_stock_raises_a_low_stock_alert(
    repo: FakeInventoryRepository,
) -> None:
    notifications = NotificationService(FakeAlertRepository())
    service = InventoryService(repo, notifications)

    batch = make_inventory_batch(current_stock=15, safety_stock=10)
    await repo.create(batch)

    await service.consume(batch.id, 10)  # 15 -> 5, now below safety_stock=10

    alerts = await notifications.list(hospital_id=batch.hospital_id)
    assert len(alerts) == 1
    assert alerts[0].type.value == "low_stock"


async def test_write_off_expired_zeroes_out_remaining_stock(
    service: InventoryService, repo: FakeInventoryRepository
) -> None:
    batch = make_inventory_batch(current_stock=30, safety_stock=0)
    await repo.create(batch)

    change = await service.write_off_expired(batch.id)

    assert change.batch.current_stock == 0
    assert change.reason == InventoryChangeReason.EXPIRY_WRITEOFF


async def test_adjust_rejects_a_decrement_past_zero(
    service: InventoryService, repo: FakeInventoryRepository
) -> None:
    batch = make_inventory_batch(current_stock=5, safety_stock=0)
    await repo.create(batch)

    with pytest.raises(InsufficientStockError):
        await service.adjust(batch.id, -10)
