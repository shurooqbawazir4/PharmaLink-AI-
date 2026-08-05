"""Hospital domain entity — plain dataclass, no ORM/framework imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.shared.enums import HospitalType


@dataclass(slots=True)
class Hospital:
    id: UUID
    name: str
    code: str
    latitude: float
    longitude: float
    city: str
    region: str
    bed_capacity: int
    occupancy_rate: float
    type: HospitalType
    is_active: bool
    created_at: datetime
