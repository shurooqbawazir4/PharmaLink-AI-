"""Medicine domain entity — plain dataclass, no ORM/framework imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class Medicine:
    id: UUID
    name: str
    generic_name: str
    atc_code: str | None
    category: str
    unit: str
    unit_cost: float
    requires_refrigeration: bool
    is_controlled: bool
    is_active: bool
    created_at: datetime
