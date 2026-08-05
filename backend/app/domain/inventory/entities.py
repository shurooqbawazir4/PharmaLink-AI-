"""Inventory domain entities — plain dataclasses, no ORM/framework imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.domain.shared.enums import InventoryChangeReason


@dataclass(slots=True)
class InventoryBatch:
    id: UUID
    hospital_id: UUID
    medicine_id: UUID
    batch_number: str
    current_stock: int
    safety_stock: int
    expiry_date: date
    unit_cost_at_receipt: float
    created_at: datetime
    storage_location: str | None = None
    manufactured_date: date | None = None
    supplier_id: UUID | None = None

    @property
    def available_stock(self) -> int:
        """Stock above the safety-stock floor — what's actually free to move."""
        return max(self.current_stock - self.safety_stock, 0)


@dataclass(slots=True, frozen=True)
class InventoryChange:
    """The result of a stock-changing operation: the updated batch plus the
    history row that was written alongside it in the same transaction."""

    batch: InventoryBatch
    change_qty: int
    reason: InventoryChangeReason
    recorded_at: datetime
