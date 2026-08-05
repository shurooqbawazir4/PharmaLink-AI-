"""SQLAlchemy implementation of `app.domain.inventory.repository.InventoryRepository`.

`create` and `record_change` are the two methods that touch both
`InventoryModel` and `InventoryHistoryModel` in one flush — see the domain
Protocol's docstring for why this is deliberately the only place stock
changes and history rows are written together.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.inventory.entities import InventoryBatch, InventoryChange
from app.domain.shared.enums import InventoryChangeReason
from app.infrastructure.db.models import InventoryHistoryModel, InventoryModel


class SQLAlchemyInventoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, inventory_id: UUID) -> InventoryBatch | None:
        model = await self._db.get(InventoryModel, inventory_id)
        return self._to_entity(model) if model else None

    async def list_batches(
        self,
        *,
        hospital_id: UUID | None = None,
        medicine_id: UUID | None = None,
        expiring_within_days: int | None = None,
        below_safety_stock: bool | None = None,
    ) -> list[InventoryBatch]:
        stmt = select(InventoryModel)
        if hospital_id is not None:
            stmt = stmt.where(InventoryModel.hospital_id == hospital_id)
        if medicine_id is not None:
            stmt = stmt.where(InventoryModel.medicine_id == medicine_id)
        if expiring_within_days is not None:
            cutoff = date.today() + timedelta(days=expiring_within_days)
            stmt = stmt.where(InventoryModel.expiry_date <= cutoff)
        if below_safety_stock:
            stmt = stmt.where(InventoryModel.current_stock < InventoryModel.safety_stock)
        stmt = stmt.order_by(InventoryModel.expiry_date)
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    async def list_fefo(self, hospital_id: UUID, medicine_id: UUID) -> list[InventoryBatch]:
        stmt = (
            select(InventoryModel)
            .where(
                InventoryModel.hospital_id == hospital_id,
                InventoryModel.medicine_id == medicine_id,
                InventoryModel.current_stock > 0,
            )
            .order_by(InventoryModel.expiry_date)
        )
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    async def create(
        self,
        batch: InventoryBatch,
        *,
        reason: InventoryChangeReason = InventoryChangeReason.RECEIPT,
    ) -> InventoryBatch:
        model = InventoryModel(
            id=batch.id,
            hospital_id=batch.hospital_id,
            medicine_id=batch.medicine_id,
            batch_number=batch.batch_number,
            current_stock=batch.current_stock,
            safety_stock=batch.safety_stock,
            storage_location=batch.storage_location,
            expiry_date=batch.expiry_date,
            manufactured_date=batch.manufactured_date,
            supplier_id=batch.supplier_id,
            unit_cost_at_receipt=batch.unit_cost_at_receipt,
        )
        self._db.add(model)
        await self._db.flush()

        self._db.add(
            InventoryHistoryModel(
                recorded_at=datetime.now(UTC),
                inventory_id=model.id,
                hospital_id=model.hospital_id,
                medicine_id=model.medicine_id,
                change_qty=batch.current_stock,
                reason=reason,
            )
        )
        await self._db.flush()
        return self._to_entity(model)

    async def record_change(
        self, inventory_id: UUID, change_qty: int, reason: InventoryChangeReason
    ) -> InventoryChange:
        model = await self._db.get(InventoryModel, inventory_id)
        if model is None:
            msg = f"InventoryBatch {inventory_id} not found for record_change"
            raise ValueError(msg)

        new_stock = model.current_stock + change_qty
        if new_stock < 0:
            msg = f"record_change would drive current_stock negative ({new_stock})"
            raise ValueError(msg)
        model.current_stock = new_stock
        await self._db.flush()

        recorded_at = datetime.now(UTC)
        self._db.add(
            InventoryHistoryModel(
                recorded_at=recorded_at,
                inventory_id=model.id,
                hospital_id=model.hospital_id,
                medicine_id=model.medicine_id,
                change_qty=change_qty,
                reason=reason,
            )
        )
        await self._db.flush()

        return InventoryChange(
            batch=self._to_entity(model),
            change_qty=change_qty,
            reason=reason,
            recorded_at=recorded_at,
        )

    async def average_daily_consumption(
        self, hospital_id: UUID, medicine_id: UUID, window_days: int = 30
    ) -> float:
        since = datetime.now(UTC) - timedelta(days=window_days)
        stmt = select(func.sum(InventoryHistoryModel.change_qty)).where(
            InventoryHistoryModel.hospital_id == hospital_id,
            InventoryHistoryModel.medicine_id == medicine_id,
            InventoryHistoryModel.reason == InventoryChangeReason.CONSUMPTION,
            InventoryHistoryModel.recorded_at >= since,
        )
        # Consumption is recorded as a negative change_qty (see record_change),
        # so the sum is <= 0 — negate to get a positive units-consumed total.
        total_consumed = -((await self._db.scalar(stmt)) or 0)
        return max(total_consumed, 0) / window_days

    @staticmethod
    def _to_entity(model: InventoryModel) -> InventoryBatch:
        return InventoryBatch(
            id=model.id,
            hospital_id=model.hospital_id,
            medicine_id=model.medicine_id,
            batch_number=model.batch_number,
            current_stock=model.current_stock,
            safety_stock=model.safety_stock,
            expiry_date=model.expiry_date,
            unit_cost_at_receipt=model.unit_cost_at_receipt,
            created_at=model.created_at,
            storage_location=model.storage_location,
            manufactured_date=model.manufactured_date,
            supplier_id=model.supplier_id,
        )
