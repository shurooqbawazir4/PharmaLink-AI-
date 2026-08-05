"""Inventory use cases: receiving, consuming, writing off, and adjusting
physical stock batches — every change is recorded transactionally via
`InventoryRepository.record_change` (see docs/architecture.md).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from app.application.notifications.service import NotificationService
from app.domain.inventory.entities import InventoryBatch, InventoryChange
from app.domain.inventory.exceptions import InsufficientStockError, InventoryBatchNotFoundError
from app.domain.inventory.repository import InventoryRepository
from app.domain.shared.enums import AlertSeverity, AlertType, InventoryChangeReason

# Below this many days of safety-stock coverage, a decrement that crosses
# under `safety_stock` is worth flagging — kept as a single constant so the
# threshold is easy to find/tune later.
_LOW_STOCK_ALERT_MESSAGE = "Stock for this medicine has dropped below its safety-stock level."


class InventoryService:
    def __init__(
        self,
        inventory_repository: InventoryRepository,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._inventory = inventory_repository
        # Optional: unit tests exercise InventoryService without a real
        # NotificationService by simply omitting it (see tests/unit/fakes.py).
        self._notifications = notification_service

    async def receive_stock(
        self,
        *,
        hospital_id: UUID,
        medicine_id: UUID,
        batch_number: str,
        quantity: int,
        expiry_date: date,
        unit_cost_at_receipt: float,
        safety_stock: int = 0,
        storage_location: str | None = None,
        manufactured_date: date | None = None,
        supplier_id: UUID | None = None,
    ) -> InventoryBatch:
        if quantity <= 0:
            msg = "quantity must be positive"
            raise ValueError(msg)

        batch = InventoryBatch(
            id=uuid4(),
            hospital_id=hospital_id,
            medicine_id=medicine_id,
            batch_number=batch_number,
            current_stock=quantity,
            safety_stock=safety_stock,
            expiry_date=expiry_date,
            unit_cost_at_receipt=unit_cost_at_receipt,
            created_at=datetime.now(UTC),
            storage_location=storage_location,
            manufactured_date=manufactured_date,
            supplier_id=supplier_id,
        )
        # `create` also writes the matching `receipt` history row, atomically —
        # see SQLAlchemyInventoryRepository.create.
        return await self._inventory.create(batch)

    async def get(self, inventory_id: UUID) -> InventoryBatch:
        batch = await self._inventory.get_by_id(inventory_id)
        if batch is None:
            raise InventoryBatchNotFoundError(str(inventory_id))
        return batch

    async def list_batches(
        self, *, hospital_id: UUID | None = None, medicine_id: UUID | None = None
    ) -> list[InventoryBatch]:
        return await self._inventory.list_batches(hospital_id=hospital_id, medicine_id=medicine_id)

    async def list_expiring_soon(
        self, hospital_id: UUID | None = None, within_days: int = 30
    ) -> list[InventoryBatch]:
        return await self._inventory.list_batches(
            hospital_id=hospital_id, expiring_within_days=within_days
        )

    async def list_below_safety_stock(
        self, hospital_id: UUID | None = None
    ) -> list[InventoryBatch]:
        return await self._inventory.list_batches(hospital_id=hospital_id, below_safety_stock=True)

    async def consume(self, inventory_id: UUID, quantity: int) -> InventoryChange:
        if quantity <= 0:
            msg = "quantity must be positive"
            raise ValueError(msg)
        batch = await self.get(inventory_id)
        if batch.current_stock < quantity:
            raise InsufficientStockError(available=batch.current_stock, requested=quantity)

        change = await self._inventory.record_change(
            inventory_id, -quantity, InventoryChangeReason.CONSUMPTION
        )
        await self._maybe_alert_low_stock(change.batch)
        return change

    async def write_off_expired(self, inventory_id: UUID) -> InventoryChange:
        batch = await self.get(inventory_id)
        if batch.current_stock <= 0:
            msg = "batch has no remaining stock to write off"
            raise ValueError(msg)
        return await self._inventory.record_change(
            inventory_id, -batch.current_stock, InventoryChangeReason.EXPIRY_WRITEOFF
        )

    async def adjust(self, inventory_id: UUID, change_qty: int) -> InventoryChange:
        if change_qty == 0:
            msg = "change_qty must be non-zero"
            raise ValueError(msg)
        batch = await self.get(inventory_id)
        if batch.current_stock + change_qty < 0:
            raise InsufficientStockError(available=batch.current_stock, requested=-change_qty)

        change = await self._inventory.record_change(
            inventory_id, change_qty, InventoryChangeReason.ADJUSTMENT
        )
        if change_qty < 0:
            await self._maybe_alert_low_stock(change.batch)
        return change

    async def _maybe_alert_low_stock(self, batch: InventoryBatch) -> None:
        """Raise a `low_stock` alert once a decrement crosses under the safety
        floor. Deliberately simple for Milestone B: this can fire again on a
        later dip even if an earlier alert for the same batch is still open
        (no dedup/cooldown yet) — acceptable for an MVP, worth revisiting
        once Notifications gets a real delivery channel."""
        if self._notifications is None or batch.current_stock >= batch.safety_stock:
            return
        await self._notifications.create_alert(
            hospital_id=batch.hospital_id,
            medicine_id=batch.medicine_id,
            alert_type=AlertType.LOW_STOCK,
            severity=AlertSeverity.WARNING,
            message=_LOW_STOCK_ALERT_MESSAGE,
        )
