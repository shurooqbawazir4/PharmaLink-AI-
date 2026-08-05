"""SQLAlchemy implementation of `app.domain.procurement.repository.PurchaseOrderRepository`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.procurement.entities import PurchaseOrder
from app.domain.shared.enums import PurchaseOrderStatus
from app.infrastructure.db.models import PurchaseOrderModel


class SQLAlchemyPurchaseOrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, order_id: UUID) -> PurchaseOrder | None:
        model = await self._db.get(PurchaseOrderModel, order_id)
        return self._to_entity(model) if model else None

    async def list_orders(
        self,
        *,
        hospital_id: UUID | None = None,
        status: PurchaseOrderStatus | None = None,
        medicine_id: UUID | None = None,
    ) -> list[PurchaseOrder]:
        stmt = select(PurchaseOrderModel)
        if hospital_id is not None:
            stmt = stmt.where(PurchaseOrderModel.hospital_id == hospital_id)
        if status is not None:
            stmt = stmt.where(PurchaseOrderModel.status == status)
        if medicine_id is not None:
            stmt = stmt.where(PurchaseOrderModel.medicine_id == medicine_id)
        stmt = stmt.order_by(PurchaseOrderModel.created_at.desc())
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    async def create(self, order: PurchaseOrder) -> PurchaseOrder:
        model = PurchaseOrderModel(
            id=order.id,
            hospital_id=order.hospital_id,
            medicine_id=order.medicine_id,
            supplier_id=order.supplier_id,
            quantity=order.quantity,
            status=order.status,
            recommended_by=order.recommended_by,
            unit_cost=order.unit_cost,
            total_cost=order.total_cost,
            expected_delivery_date=order.expected_delivery_date,
        )
        self._db.add(model)
        await self._db.flush()
        return self._to_entity(model)

    async def update(self, order: PurchaseOrder) -> PurchaseOrder:
        model = await self._db.get(PurchaseOrderModel, order.id)
        if model is None:
            msg = f"PurchaseOrder {order.id} not found for update"
            raise ValueError(msg)
        model.status = order.status
        model.expected_delivery_date = order.expected_delivery_date
        await self._db.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: PurchaseOrderModel) -> PurchaseOrder:
        return PurchaseOrder(
            id=model.id,
            hospital_id=model.hospital_id,
            medicine_id=model.medicine_id,
            supplier_id=model.supplier_id,
            quantity=model.quantity,
            status=model.status,
            recommended_by=model.recommended_by,
            unit_cost=model.unit_cost,
            total_cost=model.total_cost,
            created_at=model.created_at,
            expected_delivery_date=model.expected_delivery_date,
        )
