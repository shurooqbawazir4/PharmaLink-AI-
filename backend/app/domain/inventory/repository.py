"""Repository interface for the inventory module.

`record_change` is the one method beyond the usual CRUD shape: it updates
`current_stock` and inserts the matching `InventoryHistory` row as a single
transaction. Every later "this action changes stock" flow (Transfers,
Procurement receipt) goes through this one method rather than writing
history rows ad hoc — see docs/architecture.md.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.inventory.entities import InventoryBatch, InventoryChange
from app.domain.shared.enums import InventoryChangeReason


class InventoryRepository(Protocol):
    async def get_by_id(self, inventory_id: UUID) -> InventoryBatch | None: ...

    async def list_batches(
        self,
        *,
        hospital_id: UUID | None = None,
        medicine_id: UUID | None = None,
        expiring_within_days: int | None = None,
        below_safety_stock: bool | None = None,
    ) -> list[InventoryBatch]: ...

    async def list_fefo(self, hospital_id: UUID, medicine_id: UUID) -> list[InventoryBatch]:
        """Batches with stock > 0 for this hospital+medicine, oldest expiry first —
        the draw order for consumption, transfers, and write-offs (FEFO)."""
        ...

    async def create(
        self,
        batch: InventoryBatch,
        *,
        reason: InventoryChangeReason = InventoryChangeReason.RECEIPT,
    ) -> InventoryBatch:
        """Insert a new physical batch and its opening `InventoryHistory` row,
        atomically. `reason` defaults to `receipt` (a normal procurement
        delivery) but Transfers passes `transfer_in` when the batch's stock
        is arriving from another hospital rather than a supplier."""
        ...

    async def record_change(
        self, inventory_id: UUID, change_qty: int, reason: InventoryChangeReason
    ) -> InventoryChange:
        """Apply `change_qty` (positive or negative) to `current_stock` and insert
        the matching `InventoryHistory` row, atomically."""
        ...

    async def average_daily_consumption(
        self, hospital_id: UUID, medicine_id: UUID, window_days: int = 30
    ) -> float:
        """Mean units/day consumed (reason=consumption) over the trailing
        `window_days` — the demand signal Expiry's naive scorer and
        Procurement's naive recommender both use until Milestone C's real
        forecaster replaces it."""
        ...
