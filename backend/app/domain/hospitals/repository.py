"""Repository interface for the hospitals module."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.hospitals.entities import Hospital


class HospitalRepository(Protocol):
    async def get_by_id(self, hospital_id: UUID) -> Hospital | None: ...

    async def get_by_code(self, code: str) -> Hospital | None: ...

    async def list(
        self, *, region: str | None = None, is_active: bool | None = True
    ) -> list[Hospital]: ...

    async def create(self, hospital: Hospital) -> Hospital: ...

    async def update(self, hospital: Hospital) -> Hospital: ...
