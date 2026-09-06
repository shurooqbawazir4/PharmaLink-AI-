"""Auth domain entities — plain dataclasses, no ORM/framework imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class Role:
    id: UUID
    name: str
    permissions: list[str] = field(default_factory=list)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or "*" in self.permissions


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    hashed_password: str
    full_name: str
    role_name: str
    is_active: bool
    created_at: datetime
    hospital_id: UUID | None = None

    permissions: list[str] = field(default_factory=list)

    @property
    def has_full_access(self) -> bool:
        return self.role_name == "admin" or "*" in self.permissions
