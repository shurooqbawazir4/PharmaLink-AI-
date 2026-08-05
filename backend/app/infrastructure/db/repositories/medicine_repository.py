"""SQLAlchemy implementation of `app.domain.medicines.repository.MedicineRepository`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.medicines.entities import Medicine
from app.infrastructure.db.models import MedicineModel


class SQLAlchemyMedicineRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, medicine_id: UUID) -> Medicine | None:
        model = await self._db.get(MedicineModel, medicine_id)
        return self._to_entity(model) if model else None

    async def list(
        self, *, category: str | None = None, is_active: bool | None = True
    ) -> list[Medicine]:
        stmt = select(MedicineModel)
        if category is not None:
            stmt = stmt.where(MedicineModel.category == category)
        if is_active is not None:
            stmt = stmt.where(MedicineModel.is_active == is_active)
        stmt = stmt.order_by(MedicineModel.name)
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    async def create(self, medicine: Medicine) -> Medicine:
        model = MedicineModel(
            id=medicine.id,
            name=medicine.name,
            generic_name=medicine.generic_name,
            atc_code=medicine.atc_code,
            category=medicine.category,
            unit=medicine.unit,
            unit_cost=medicine.unit_cost,
            requires_refrigeration=medicine.requires_refrigeration,
            is_controlled=medicine.is_controlled,
            is_active=medicine.is_active,
        )
        self._db.add(model)
        await self._db.flush()
        return self._to_entity(model)

    async def update(self, medicine: Medicine) -> Medicine:
        model = await self._db.get(MedicineModel, medicine.id)
        if model is None:
            msg = f"Medicine {medicine.id} not found for update"
            raise ValueError(msg)
        model.name = medicine.name
        model.generic_name = medicine.generic_name
        model.atc_code = medicine.atc_code
        model.category = medicine.category
        model.unit = medicine.unit
        model.unit_cost = medicine.unit_cost
        model.requires_refrigeration = medicine.requires_refrigeration
        model.is_controlled = medicine.is_controlled
        model.is_active = medicine.is_active
        await self._db.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: MedicineModel) -> Medicine:
        return Medicine(
            id=model.id,
            name=model.name,
            generic_name=model.generic_name,
            atc_code=model.atc_code,
            category=model.category,
            unit=model.unit,
            unit_cost=model.unit_cost,
            requires_refrigeration=model.requires_refrigeration,
            is_controlled=model.is_controlled,
            is_active=model.is_active,
            created_at=model.created_at,
        )
