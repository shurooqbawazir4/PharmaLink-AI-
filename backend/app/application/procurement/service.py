"""Procurement use cases: AI-recommended purchase orders and their
lifecycle (recommended -> approved -> ordered -> received).

Depends on `PurchaseOrderRepository`, `SupplierRepository`,
`InventoryRepository` (for stock/consumption signals — a cross-module
application-layer collaboration, same as Transfers) and `InventoryService`
(reused directly for `mark_received`, since "receive a physical batch" is
already a well-defined use case there — no reason to duplicate its
transactional create+history logic here).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from app.application.inventory.service import InventoryService
from app.domain.inventory.entities import InventoryBatch
from app.domain.inventory.repository import InventoryRepository
from app.domain.procurement.entities import PurchaseOrder, Supplier
from app.domain.procurement.exceptions import (
    InvalidPurchaseOrderStateError,
    PurchaseOrderNotFoundError,
)
from app.domain.procurement.recommender import ProcurementRecommender
from app.domain.procurement.repository import PurchaseOrderRepository, SupplierRepository
from app.domain.shared.enums import PurchaseOrderStatus, RecommendedBy


class ProcurementService:
    def __init__(
        self,
        order_repository: PurchaseOrderRepository,
        supplier_repository: SupplierRepository,
        inventory_repository: InventoryRepository,
        inventory_service: InventoryService,
        recommender: ProcurementRecommender,
    ) -> None:
        self._orders = order_repository
        self._suppliers = supplier_repository
        self._inventory = inventory_repository
        self._inventory_service = inventory_service
        self._recommender = recommender

    async def recommend_for_hospital(self, hospital_id: UUID) -> list[PurchaseOrder]:
        """Evaluate every medicine currently stocked at `hospital_id` and
        create a `recommended`/`ai` purchase order for any that need
        reordering. Medicines with no inventory history at this hospital
        aren't considered — there's no stock signal to reorder against."""
        batches = await self._inventory.list_batches(hospital_id=hospital_id)
        by_medicine: dict[UUID, list[InventoryBatch]] = defaultdict(list)
        for batch in batches:
            by_medicine[batch.medicine_id].append(batch)

        created_orders: list[PurchaseOrder] = []
        for medicine_id, medicine_batches in by_medicine.items():
            supplier = await self._select_supplier(medicine_batches)
            if supplier is None:
                continue  # no active supplier to order from — skip rather than fail the whole batch

            current_stock = sum(batch.current_stock for batch in medicine_batches)
            safety_stock = sum(batch.safety_stock for batch in medicine_batches)
            avg_daily_consumption = await self._inventory.average_daily_consumption(
                hospital_id, medicine_id
            )
            reference_batch = max(medicine_batches, key=lambda batch: batch.created_at)

            recommendation = self._recommender.recommend(
                current_stock=current_stock,
                safety_stock=safety_stock,
                avg_daily_consumption=avg_daily_consumption,
                unit_cost=reference_batch.unit_cost_at_receipt,
                supplier=supplier,
            )
            if recommendation is None:
                continue

            order = PurchaseOrder(
                id=uuid4(),
                hospital_id=hospital_id,
                medicine_id=medicine_id,
                supplier_id=supplier.id,
                quantity=recommendation.quantity,
                status=PurchaseOrderStatus.RECOMMENDED,
                recommended_by=RecommendedBy.AI,
                unit_cost=recommendation.unit_cost,
                total_cost=round(recommendation.quantity * recommendation.unit_cost, 2),
                created_at=datetime.now(UTC),
                expected_delivery_date=recommendation.expected_delivery_date,
            )
            created_orders.append(await self._orders.create(order))

        return created_orders

    async def get(self, order_id: UUID) -> PurchaseOrder:
        order = await self._orders.get_by_id(order_id)
        if order is None:
            raise PurchaseOrderNotFoundError(str(order_id))
        return order

    async def list_orders(
        self,
        *,
        hospital_id: UUID | None = None,
        status: PurchaseOrderStatus | None = None,
        medicine_id: UUID | None = None,
    ) -> list[PurchaseOrder]:
        return await self._orders.list_orders(
            hospital_id=hospital_id, status=status, medicine_id=medicine_id
        )

    async def approve(self, order_id: UUID) -> PurchaseOrder:
        order = await self.get(order_id)
        self._require_status(order, PurchaseOrderStatus.RECOMMENDED, "approve")
        order.status = PurchaseOrderStatus.APPROVED
        return await self._orders.update(order)

    async def mark_ordered(self, order_id: UUID) -> PurchaseOrder:
        order = await self.get(order_id)
        self._require_status(order, PurchaseOrderStatus.APPROVED, "mark as ordered")
        order.status = PurchaseOrderStatus.ORDERED
        return await self._orders.update(order)

    async def mark_received(
        self, order_id: UUID, *, batch_number: str, expiry_date: date
    ) -> PurchaseOrder:
        order = await self.get(order_id)
        self._require_status(order, PurchaseOrderStatus.ORDERED, "mark as received")

        await self._inventory_service.receive_stock(
            hospital_id=order.hospital_id,
            medicine_id=order.medicine_id,
            batch_number=batch_number,
            quantity=order.quantity,
            expiry_date=expiry_date,
            unit_cost_at_receipt=order.unit_cost,
            supplier_id=order.supplier_id,
        )
        order.status = PurchaseOrderStatus.RECEIVED
        return await self._orders.update(order)

    async def cancel(self, order_id: UUID) -> PurchaseOrder:
        order = await self.get(order_id)
        if order.status in (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED):
            raise InvalidPurchaseOrderStateError(current_status=order.status.value, action="cancel")
        order.status = PurchaseOrderStatus.CANCELLED
        return await self._orders.update(order)

    @staticmethod
    def _require_status(
        order: PurchaseOrder, expected: PurchaseOrderStatus, action: str
    ) -> None:
        if order.status != expected:
            raise InvalidPurchaseOrderStateError(current_status=order.status.value, action=action)

    async def _select_supplier(self, medicine_batches: list[InventoryBatch]) -> Supplier | None:
        """Prefer whichever supplier most recently delivered this medicine to
        this hospital (tracked on `InventoryBatch.supplier_id`); fall back to
        the most reliable active supplier network-wide if there's no history
        or that supplier's gone inactive."""
        recent_with_supplier = [b for b in medicine_batches if b.supplier_id is not None]
        if recent_with_supplier:
            candidate_id = max(recent_with_supplier, key=lambda b: b.created_at).supplier_id
            assert candidate_id is not None  # narrowed by the `is not None` filter above
            candidate = await self._suppliers.get_by_id(candidate_id)
            if candidate is not None and candidate.is_active:
                return candidate

        active_suppliers = await self._suppliers.list_suppliers(is_active=True)
        return active_suppliers[0] if active_suppliers else None
