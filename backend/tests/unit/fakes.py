"""In-memory fake repositories used by unit tests.

Each fake implements the corresponding domain `Protocol` exactly — this is
what lets `HospitalService`/`MedicineService` be tested with zero database,
zero Docker, and zero network I/O.
"""

from __future__ import annotations

from uuid import UUID

from app.domain.hospitals.entities import Hospital
from app.domain.medicines.entities import Medicine


class FakeHospitalRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Hospital] = {}

    async def get_by_id(self, hospital_id: UUID) -> Hospital | None:
        return self._by_id.get(hospital_id)

    async def get_by_code(self, code: str) -> Hospital | None:
        return next((h for h in self._by_id.values() if h.code == code), None)

    async def list(
        self, *, region: str | None = None, is_active: bool | None = True
    ) -> list[Hospital]:
        hospitals = self._by_id.values()
        if region is not None:
            hospitals = [h for h in hospitals if h.region == region]
        if is_active is not None:
            hospitals = [h for h in hospitals if h.is_active == is_active]
        return sorted(hospitals, key=lambda h: h.name)

    async def create(self, hospital: Hospital) -> Hospital:
        self._by_id[hospital.id] = hospital
        return hospital

    async def update(self, hospital: Hospital) -> Hospital:
        self._by_id[hospital.id] = hospital
        return hospital


class FakeMedicineRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Medicine] = {}

    async def get_by_id(self, medicine_id: UUID) -> Medicine | None:
        return self._by_id.get(medicine_id)

    async def list(
        self, *, category: str | None = None, is_active: bool | None = True
    ) -> list[Medicine]:
        medicines = self._by_id.values()
        if category is not None:
            medicines = [m for m in medicines if m.category == category]
        if is_active is not None:
            medicines = [m for m in medicines if m.is_active == is_active]
        return sorted(medicines, key=lambda m: m.name)

    async def create(self, medicine: Medicine) -> Medicine:
        self._by_id[medicine.id] = medicine
        return medicine

    async def update(self, medicine: Medicine) -> Medicine:
        self._by_id[medicine.id] = medicine
        return medicine
