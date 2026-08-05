"""Repository interface for the auth module.

An abstract contract only — `app/infrastructure/db/repositories/user_repository.py`
provides the SQLAlchemy implementation. Services depend on this `Protocol`,
never on the concrete class, so they stay swappable/unit-testable.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.auth.entities import User


class UserRepository(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def create(self, user: User) -> User: ...

    async def list_by_hospital(self, hospital_id: UUID) -> list[User]: ...
