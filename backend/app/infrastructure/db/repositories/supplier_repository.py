"""SQLAlchemy implementation of `app.domain.procurement.repository.SupplierRepository`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.procurement.entities import Supplier
from app.infrastructure.db.models import SupplierModel


class SQLAlchemySupplierRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, supplier_id: UUID) -> Supplier | None:
        model = await self._db.get(SupplierModel, supplier_id)
        return self._to_entity(model) if model else None

    async def list_suppliers(self, *, is_active: bool | None = True) -> list[Supplier]:
        stmt = select(SupplierModel)
        if is_active is not None:
            stmt = stmt.where(SupplierModel.is_active == is_active)
        stmt = stmt.order_by(SupplierModel.reliability_score.desc())
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    async def create(self, supplier: Supplier) -> Supplier:
        model = SupplierModel(
            id=supplier.id,
            name=supplier.name,
            contact_email=supplier.contact_email,
            lead_time_days=supplier.lead_time_days,
            reliability_score=supplier.reliability_score,
            is_active=supplier.is_active,
        )
        self._db.add(model)
        await self._db.flush()
        return self._to_entity(model)

    async def update(self, supplier: Supplier) -> Supplier:
        model = await self._db.get(SupplierModel, supplier.id)
        if model is None:
            msg = f"Supplier {supplier.id} not found for update"
            raise ValueError(msg)
        model.name = supplier.name
        model.contact_email = supplier.contact_email
        model.lead_time_days = supplier.lead_time_days
        model.reliability_score = supplier.reliability_score
        model.is_active = supplier.is_active
        await self._db.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: SupplierModel) -> Supplier:
        return Supplier(
            id=model.id,
            name=model.name,
            contact_email=model.contact_email,
            lead_time_days=model.lead_time_days,
            reliability_score=model.reliability_score,
            is_active=model.is_active,
            created_at=model.created_at,
        )
