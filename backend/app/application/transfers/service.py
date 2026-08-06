"""Transfer use cases — the core value-prop flow: propose -> approve ->
complete, moving physical stock between hospitals via `InventoryRepository`.

Depends on `TransferRepository`, `InventoryRepository`, and
`HospitalRepository` — a legitimate cross-module application-layer
collaboration (domain layers stay isolated; application layers may
compose). `distance_km`/`transportation_cost` stay a simple haversine-based
estimate (still the right unit-cost model at this scale) — Milestone C's
`OptimizationService` (application/optimization/service.py) is the one
that got smarter: it calls `propose()` the same way a human does, just
computed *which* transfers to propose across a whole network via OR-Tools,
tagging them `recommended_by=RecommendedBy.AI`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from app.domain.hospitals.exceptions import HospitalNotFoundError
from app.domain.hospitals.repository import HospitalRepository
from app.domain.inventory.entities import InventoryBatch
from app.domain.inventory.repository import InventoryRepository
from app.domain.shared.enums import InventoryChangeReason, RecommendedBy, TransferStatus
from app.domain.shared.geo import haversine_km
from app.domain.transfers.entities import Transfer
from app.domain.transfers.exceptions import (
    InsufficientAvailableStockError,
    InvalidTransferStateError,
    SameHospitalTransferError,
    TransferNotFoundError,
)
from app.domain.transfers.repository import TransferRepository

# A simple $/km haversine-based estimate — good enough at this scale; see
# the module docstring for why this didn't need to get fancier in Milestone C.
_TRANSPORT_COST_PER_KM = 2.5
_EXPIRY_RISK_WINDOW_DAYS = 30


class TransferService:
    def __init__(
        self,
        transfer_repository: TransferRepository,
        inventory_repository: InventoryRepository,
        hospital_repository: HospitalRepository,
    ) -> None:
        self._transfers = transfer_repository
        self._inventory = inventory_repository
        self._hospitals = hospital_repository

    async def propose(
        self,
        *,
        source_hospital_id: UUID,
        destination_hospital_id: UUID,
        medicine_id: UUID,
        quantity: int,
        created_by: UUID | None = None,
        recommended_by: RecommendedBy = RecommendedBy.MANUAL,
    ) -> Transfer:
        if quantity <= 0:
            msg = "quantity must be positive"
            raise ValueError(msg)
        if source_hospital_id == destination_hospital_id:
            raise SameHospitalTransferError()

        source_batches = await self._inventory.list_fefo(source_hospital_id, medicine_id)
        available = sum(batch.available_stock for batch in source_batches)
        if available < quantity:
            raise InsufficientAvailableStockError(available=available, requested=quantity)

        source_hospital = await self._hospitals.get_by_id(source_hospital_id)
        destination_hospital = await self._hospitals.get_by_id(destination_hospital_id)
        if source_hospital is None:
            raise HospitalNotFoundError(str(source_hospital_id))
        if destination_hospital is None:
            raise HospitalNotFoundError(str(destination_hospital_id))

        distance_km = haversine_km(
            source_hospital.latitude,
            source_hospital.longitude,
            destination_hospital.latitude,
            destination_hospital.longitude,
        )

        transfer = Transfer(
            id=uuid4(),
            source_hospital_id=source_hospital_id,
            destination_hospital_id=destination_hospital_id,
            medicine_id=medicine_id,
            quantity=quantity,
            status=TransferStatus.PROPOSED,
            created_at=datetime.now(UTC),
            created_by=created_by,
            recommended_by=recommended_by,
            distance_km=round(distance_km, 2),
            transportation_cost=round(distance_km * _TRANSPORT_COST_PER_KM, 2),
        )
        return await self._transfers.create(transfer)

    async def get(self, transfer_id: UUID) -> Transfer:
        transfer = await self._transfers.get_by_id(transfer_id)
        if transfer is None:
            raise TransferNotFoundError(str(transfer_id))
        return transfer

    async def list_transfers(
        self,
        *,
        hospital_id: UUID | None = None,
        status: TransferStatus | None = None,
        medicine_id: UUID | None = None,
    ) -> list[Transfer]:
        return await self._transfers.list_transfers(
            hospital_id=hospital_id, status=status, medicine_id=medicine_id
        )

    async def approve(self, transfer_id: UUID) -> Transfer:
        transfer = await self.get(transfer_id)
        if transfer.status != TransferStatus.PROPOSED:
            raise InvalidTransferStateError(current_status=transfer.status.value, action="approve")
        transfer.status = TransferStatus.APPROVED
        return await self._transfers.update(transfer)

    async def complete(self, transfer_id: UUID) -> Transfer:
        transfer = await self.get(transfer_id)
        if transfer.status != TransferStatus.APPROVED:
            raise InvalidTransferStateError(current_status=transfer.status.value, action="complete")

        source_batches = await self._inventory.list_fefo(
            transfer.source_hospital_id, transfer.medicine_id
        )
        remaining = transfer.quantity
        expiry_prevented_value = 0.0

        for batch in source_batches:
            if remaining <= 0:
                break
            draw = min(batch.available_stock, remaining)
            if draw <= 0:
                continue

            await self._inventory.record_change(
                batch.id, -draw, InventoryChangeReason.TRANSFER_OUT
            )
            await self._receive_at_destination(transfer, batch, draw)

            if (batch.expiry_date - date.today()).days <= _EXPIRY_RISK_WINDOW_DAYS:
                expiry_prevented_value += draw * batch.unit_cost_at_receipt
            remaining -= draw

        if remaining > 0:
            # Stock moved between approve() and complete() (a race). Raising
            # here rolls back everything above via the request-scoped DB
            # session (see core/database.py::get_db) — flush() pushed these
            # writes to the DB but nothing commits until the request
            # finishes successfully, so a partial draw never persists.
            raise InsufficientAvailableStockError(
                available=transfer.quantity - remaining, requested=transfer.quantity
            )

        transfer.status = TransferStatus.COMPLETED
        transfer.completed_at = datetime.now(UTC)
        transfer.expiry_prevented_value = round(expiry_prevented_value, 2)
        return await self._transfers.update(transfer)

    async def cancel(self, transfer_id: UUID) -> Transfer:
        transfer = await self.get(transfer_id)
        if transfer.status not in (TransferStatus.PROPOSED, TransferStatus.APPROVED):
            raise InvalidTransferStateError(current_status=transfer.status.value, action="cancel")
        transfer.status = TransferStatus.CANCELLED
        return await self._transfers.update(transfer)

    async def _receive_at_destination(
        self, transfer: Transfer, source_batch: InventoryBatch, quantity: int
    ) -> None:
        """Create the matching stock at the destination hospital, preserving
        the physical batch's identity (batch number, expiry, unit cost) —
        the same medicine batch now just lives at a different hospital."""
        destination_batch = InventoryBatch(
            id=uuid4(),
            hospital_id=transfer.destination_hospital_id,
            medicine_id=transfer.medicine_id,
            batch_number=source_batch.batch_number,
            current_stock=quantity,
            safety_stock=0,
            expiry_date=source_batch.expiry_date,
            unit_cost_at_receipt=source_batch.unit_cost_at_receipt,
            created_at=datetime.now(UTC),
            supplier_id=source_batch.supplier_id,
        )
        await self._inventory.create(destination_batch, reason=InventoryChangeReason.TRANSFER_IN)
