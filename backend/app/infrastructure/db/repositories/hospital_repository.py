"""SQLAlchemy implementation of `app.domain.hospitals.repository.HospitalRepository`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.hospitals.entities import Hospital
from app.infrastructure.db.models import HospitalModel


class SQLAlchemyHospitalRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, hospital_id: UUID) -> Hospital | None:
        model = await self._db.get(HospitalModel, hospital_id)
        return self._to_entity(model) if model else None

    async def get_by_code(self, code: str) -> Hospital | None:
        stmt = select(HospitalModel).where(HospitalModel.code == code)
        model = await self._db.scalar(stmt)
        return self._to_entity(model) if model else None

    async def list(
        self, *, region: str | None = None, is_active: bool | None = True
    ) -> list[Hospital]:
        stmt = select(HospitalModel)
        if region is not None:
            stmt = stmt.where(HospitalModel.region == region)
        if is_active is not None:
            stmt = stmt.where(HospitalModel.is_active == is_active)
        stmt = stmt.order_by(HospitalModel.name)
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    async def create(self, hospital: Hospital) -> Hospital:
        model = HospitalModel(
            id=hospital.id,
            name=hospital.name,
            code=hospital.code,
            latitude=hospital.latitude,
            longitude=hospital.longitude,
            city=hospital.city,
            region=hospital.region,
            bed_capacity=hospital.bed_capacity,
            occupancy_rate=hospital.occupancy_rate,
            type=hospital.type,
            is_active=hospital.is_active,
        )
        self._db.add(model)
        await self._db.flush()
        return self._to_entity(model)

    async def update(self, hospital: Hospital) -> Hospital:
        model = await self._db.get(HospitalModel, hospital.id)
        if model is None:
            msg = f"Hospital {hospital.id} not found for update"
            raise ValueError(msg)
        model.name = hospital.name
        model.code = hospital.code
        model.latitude = hospital.latitude
        model.longitude = hospital.longitude
        model.city = hospital.city
        model.region = hospital.region
        model.bed_capacity = hospital.bed_capacity
        model.occupancy_rate = hospital.occupancy_rate
        model.type = hospital.type
        model.is_active = hospital.is_active
        await self._db.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: HospitalModel) -> Hospital:
        return Hospital(
            id=model.id,
            name=model.name,
            code=model.code,
            latitude=model.latitude,
            longitude=model.longitude,
            city=model.city,
            region=model.region,
            bed_capacity=model.bed_capacity,
            occupancy_rate=model.occupancy_rate,
            type=model.type,
            is_active=model.is_active,
            created_at=model.created_at,
        )
