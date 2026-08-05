"""Medicine use cases: the catalogue every inventory/forecast/order references."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.medicines.entities import Medicine
from app.domain.medicines.exceptions import MedicineNotFoundError
from app.domain.medicines.repository import MedicineRepository


class MedicineService:
    def __init__(self, medicine_repository: MedicineRepository) -> None:
        self._medicines = medicine_repository

    async def create(
        self,
        *,
        name: str,
        generic_name: str,
        category: str,
        unit: str,
        unit_cost: float,
        atc_code: str | None = None,
        requires_refrigeration: bool = False,
        is_controlled: bool = False,
    ) -> Medicine:
        if unit_cost <= 0:
            msg = "unit_cost must be a positive number"
            raise ValueError(msg)

        medicine = Medicine(
            id=uuid4(),
            name=name,
            generic_name=generic_name,
            atc_code=atc_code,
            category=category,
            unit=unit,
            unit_cost=unit_cost,
            requires_refrigeration=requires_refrigeration,
            is_controlled=is_controlled,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        return await self._medicines.create(medicine)

    async def get(self, medicine_id: UUID) -> Medicine:
        medicine = await self._medicines.get_by_id(medicine_id)
        if medicine is None:
            raise MedicineNotFoundError(str(medicine_id))
        return medicine

    async def list(
        self, *, category: str | None = None, include_inactive: bool = False
    ) -> list[Medicine]:
        return await self._medicines.list(
            category=category, is_active=None if include_inactive else True
        )

    async def update_unit_cost(self, medicine_id: UUID, unit_cost: float) -> Medicine:
        if unit_cost <= 0:
            msg = "unit_cost must be a positive number"
            raise ValueError(msg)
        medicine = await self.get(medicine_id)
        medicine.unit_cost = unit_cost
        return await self._medicines.update(medicine)

    async def deactivate(self, medicine_id: UUID) -> Medicine:
        medicine = await self.get(medicine_id)
        medicine.is_active = False
        return await self._medicines.update(medicine)
