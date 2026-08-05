"""Unit tests for ProcurementService — recommend/approve/mark-ordered/receive."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.application.inventory.service import InventoryService
from app.application.procurement.service import ProcurementService
from app.domain.procurement.entities import PurchaseOrder
from app.domain.shared.enums import (
    InventoryChangeReason,
    PurchaseOrderStatus,
    RecommendedBy,
)
from app.infrastructure.external.naive_procurement_recommender import (
    NaiveProcurementRecommender,
)
from tests.unit.fakes import (
    FakeInventoryRepository,
    FakePurchaseOrderRepository,
    FakeSupplierRepository,
    make_inventory_batch,
    make_supplier,
)


@pytest.fixture
def inventory_repo() -> FakeInventoryRepository:
    return FakeInventoryRepository()


@pytest.fixture
def supplier_repo() -> FakeSupplierRepository:
    return FakeSupplierRepository()


@pytest.fixture
def order_repo() -> FakePurchaseOrderRepository:
    return FakePurchaseOrderRepository()


@pytest.fixture
def service(
    order_repo: FakePurchaseOrderRepository,
    supplier_repo: FakeSupplierRepository,
    inventory_repo: FakeInventoryRepository,
) -> ProcurementService:
    inventory_service = InventoryService(inventory_repo)
    return ProcurementService(
        order_repo, supplier_repo, inventory_repo, inventory_service, NaiveProcurementRecommender()
    )


async def test_recommend_skips_medicine_with_no_active_supplier(
    service: ProcurementService, inventory_repo: FakeInventoryRepository
) -> None:
    hospital_id, medicine_id = uuid.uuid4(), uuid.uuid4()
    await inventory_repo.create(
        make_inventory_batch(hospital_id=hospital_id, medicine_id=medicine_id, current_stock=1)
    )

    orders = await service.recommend_for_hospital(hospital_id)

    assert orders == []


async def test_recommend_creates_an_order_when_stock_is_low(
    service: ProcurementService,
    inventory_repo: FakeInventoryRepository,
    supplier_repo: FakeSupplierRepository,
) -> None:
    hospital_id, medicine_id = uuid.uuid4(), uuid.uuid4()
    supplier = await supplier_repo.create(make_supplier(lead_time_days=7))
    # Start with 320, consume 300 over the trailing window (avg 10/day),
    # leaving 20 on hand.
    batch = make_inventory_batch(
        hospital_id=hospital_id, medicine_id=medicine_id, current_stock=320, safety_stock=10
    )
    batch.supplier_id = supplier.id
    await inventory_repo.create(batch)
    # ~10 units/day consumption -> reorder point (10*7 + 10 = 80) exceeds
    # current_stock (20), so a reorder should fire.
    await inventory_repo.record_change(batch.id, -300, InventoryChangeReason.CONSUMPTION)

    orders = await service.recommend_for_hospital(hospital_id)

    assert len(orders) == 1
    assert orders[0].status == PurchaseOrderStatus.RECOMMENDED
    assert orders[0].supplier_id == supplier.id
    assert orders[0].quantity > 0


async def test_recommend_prefers_the_most_recently_used_supplier(
    service: ProcurementService,
    inventory_repo: FakeInventoryRepository,
    supplier_repo: FakeSupplierRepository,
) -> None:
    hospital_id, medicine_id = uuid.uuid4(), uuid.uuid4()
    older_supplier = await supplier_repo.create(make_supplier(reliability_score=0.99))
    newer_supplier = await supplier_repo.create(make_supplier(reliability_score=0.5))

    # Start with 305, consume 300 over the trailing window (avg 10/day),
    # leaving 5 on hand — combined with newer_batch's 5, reorder fires.
    older_batch = make_inventory_batch(
        hospital_id=hospital_id, medicine_id=medicine_id, current_stock=305, safety_stock=5
    )
    older_batch.supplier_id = older_supplier.id
    await inventory_repo.create(older_batch)

    newer_batch = make_inventory_batch(
        hospital_id=hospital_id, medicine_id=medicine_id, current_stock=5, safety_stock=5
    )
    newer_batch.supplier_id = newer_supplier.id
    newer_batch.created_at = older_batch.created_at + timedelta(days=1)
    await inventory_repo.create(newer_batch)

    await inventory_repo.record_change(older_batch.id, -300, InventoryChangeReason.CONSUMPTION)

    orders = await service.recommend_for_hospital(hospital_id)

    assert len(orders) == 1
    assert orders[0].supplier_id == newer_supplier.id


async def test_mark_received_transitions_order_and_creates_inventory(
    service: ProcurementService,
    inventory_repo: FakeInventoryRepository,
    supplier_repo: FakeSupplierRepository,
    order_repo: FakePurchaseOrderRepository,
) -> None:
    hospital_id, medicine_id = uuid.uuid4(), uuid.uuid4()
    supplier = await supplier_repo.create(make_supplier())
    order = await order_repo.create(
        PurchaseOrder(
            id=uuid.uuid4(),
            hospital_id=hospital_id,
            medicine_id=medicine_id,
            supplier_id=supplier.id,
            quantity=50,
            status=PurchaseOrderStatus.ORDERED,
            recommended_by=RecommendedBy.AI,
            unit_cost=3.0,
            total_cost=150.0,
            created_at=datetime.now(UTC),
        )
    )

    received = await service.mark_received(
        order.id, batch_number="PO-BATCH-1", expiry_date=date.today() + timedelta(days=200)
    )

    assert received.status == PurchaseOrderStatus.RECEIVED
    new_batches = await inventory_repo.list_batches(
        hospital_id=hospital_id, medicine_id=medicine_id
    )
    assert sum(b.current_stock for b in new_batches) == 50
