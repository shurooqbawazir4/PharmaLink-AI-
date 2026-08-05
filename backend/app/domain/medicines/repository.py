"""Repository interface for the medicines module."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.medicines.entities import Medicine


class MedicineRepository(Protocol):
    async def get_by_id(self, medicine_id: UUID) -> Medicine | None: ...

    async def list(
        self, *, category: str | None = None, is_active: bool | None = True
    ) -> list[Medicine]: ...

    async def create(self, medicine: Medicine) -> Medicine: ...

    async def update(self, medicine: Medicine) -> Medicine: ...
