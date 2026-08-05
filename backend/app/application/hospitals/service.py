"""Hospital use cases: registry of hospital network nodes.

Every other module (inventory, transfers, forecasts, ...) references
hospitals by id, so this stays a small, stable CRUD-plus-invariants service.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.hospitals.entities import Hospital
from app.domain.hospitals.exceptions import HospitalCodeAlreadyExistsError, HospitalNotFoundError
from app.domain.hospitals.repository import HospitalRepository
from app.domain.shared.enums import HospitalType


class HospitalService:
    def __init__(self, hospital_repository: HospitalRepository) -> None:
        self._hospitals = hospital_repository

    async def create(
        self,
        *,
        name: str,
        code: str,
        latitude: float,
        longitude: float,
        city: str,
        region: str,
        bed_capacity: int,
        hospital_type: HospitalType,
        occupancy_rate: float = 0.0,
    ) -> Hospital:
        normalized_code = code.strip().upper()
        if await self._hospitals.get_by_code(normalized_code) is not None:
            raise HospitalCodeAlreadyExistsError(normalized_code)

        hospital = Hospital(
            id=uuid4(),
            name=name,
            code=normalized_code,
            latitude=latitude,
            longitude=longitude,
            city=city,
            region=region,
            bed_capacity=bed_capacity,
            occupancy_rate=occupancy_rate,
            type=hospital_type,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        return await self._hospitals.create(hospital)

    async def get(self, hospital_id: UUID) -> Hospital:
        hospital = await self._hospitals.get_by_id(hospital_id)
        if hospital is None:
            raise HospitalNotFoundError(str(hospital_id))
        return hospital

    async def list(
        self, *, region: str | None = None, include_inactive: bool = False
    ) -> list[Hospital]:
        return await self._hospitals.list(
            region=region, is_active=None if include_inactive else True
        )

    async def update_occupancy(self, hospital_id: UUID, occupancy_rate: float) -> Hospital:
        if not 0.0 <= occupancy_rate <= 1.0:
            msg = "occupancy_rate must be between 0.0 and 1.0"
            raise ValueError(msg)
        hospital = await self.get(hospital_id)
        hospital.occupancy_rate = occupancy_rate
        return await self._hospitals.update(hospital)

    async def deactivate(self, hospital_id: UUID) -> Hospital:
        hospital = await self.get(hospital_id)
        hospital.is_active = False
        return await self._hospitals.update(hospital)
