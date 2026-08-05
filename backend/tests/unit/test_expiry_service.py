"""Unit tests for ExpiryService + NaiveExpiryScorer."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.application.expiry.service import ExpiryService
from app.application.notifications.service import NotificationService
from app.domain.inventory.exceptions import InventoryBatchNotFoundError
from app.domain.shared.enums import InventoryChangeReason
from app.infrastructure.external.naive_expiry_scorer import NaiveExpiryScorer
from tests.unit.fakes import (
    FakeAlertRepository,
    FakeExpiryRiskRepository,
    FakeInventoryRepository,
    make_inventory_batch,
)


@pytest.fixture
def inventory_repo() -> FakeInventoryRepository:
    return FakeInventoryRepository()


@pytest.fixture
def expiry_repo() -> FakeExpiryRiskRepository:
    return FakeExpiryRiskRepository()


@pytest.fixture
def service(
    expiry_repo: FakeExpiryRiskRepository, inventory_repo: FakeInventoryRepository
) -> ExpiryService:
    return ExpiryService(expiry_repo, inventory_repo, NaiveExpiryScorer())


async def test_evaluate_missing_batch_raises_not_found(service: ExpiryService) -> None:
    with pytest.raises(InventoryBatchNotFoundError):
        await service.evaluate_batch(uuid.uuid4())


async def test_far_dated_batch_with_healthy_consumption_scores_low_risk(
    service: ExpiryService, inventory_repo: FakeInventoryRepository
) -> None:
    # Start with 250, consume 150 over the trailing window (avg ~5/day),
    # leaving 100 on hand — sells through in ~20 days, expiry is a year out.
    batch = make_inventory_batch(
        current_stock=250, expiry_date=date.today() + timedelta(days=365)
    )
    await inventory_repo.create(batch)
    await inventory_repo.record_change(batch.id, -150, InventoryChangeReason.CONSUMPTION)

    record = await service.evaluate_batch(batch.id)

    assert record.probability_expires_before_use < 0.5


async def test_near_dated_batch_with_no_consumption_signal_scores_high_risk(
    service: ExpiryService, inventory_repo: FakeInventoryRepository
) -> None:
    batch = make_inventory_batch(current_stock=100, expiry_date=date.today() + timedelta(days=10))
    await inventory_repo.create(batch)

    record = await service.evaluate_batch(batch.id)

    assert record.probability_expires_before_use >= 0.5


async def test_high_risk_evaluation_raises_an_alert(
    inventory_repo: FakeInventoryRepository,
) -> None:
    expiry_repo = FakeExpiryRiskRepository()
    notifications = NotificationService(FakeAlertRepository())
    service = ExpiryService(expiry_repo, inventory_repo, NaiveExpiryScorer(), notifications)

    batch = make_inventory_batch(current_stock=100, expiry_date=date.today() + timedelta(days=5))
    await inventory_repo.create(batch)

    await service.evaluate_batch(batch.id)

    alerts = await notifications.list(hospital_id=batch.hospital_id)
    assert len(alerts) == 1
    assert alerts[0].type.value == "expiry_risk"


async def test_list_high_risk_filters_by_threshold(
    service: ExpiryService, inventory_repo: FakeInventoryRepository
) -> None:
    # Zero consumption history reads as "uncertain" (0.5), not "safe" — give
    # the low-risk batch a real signal so it scores genuinely low, not just
    # unscored. See test_far_dated_batch_with_healthy_consumption_scores_low_risk.
    low_risk_batch = make_inventory_batch(
        current_stock=250, expiry_date=date.today() + timedelta(days=365)
    )
    high_risk_batch = make_inventory_batch(
        current_stock=100, expiry_date=date.today() + timedelta(days=2)
    )
    await inventory_repo.create(low_risk_batch)
    await inventory_repo.create(high_risk_batch)
    await inventory_repo.record_change(low_risk_batch.id, -150, InventoryChangeReason.CONSUMPTION)

    await service.evaluate_batch(low_risk_batch.id)
    await service.evaluate_batch(high_risk_batch.id)

    high_risk = await service.list_high_risk(threshold=0.5)
    assert {r.inventory_id for r in high_risk} == {high_risk_batch.id}
