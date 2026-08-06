"""Transfer domain entity — plain dataclass, no ORM/framework imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.shared.enums import RecommendedBy, TransferStatus


@dataclass(slots=True)
class Transfer:
    id: UUID
    source_hospital_id: UUID
    destination_hospital_id: UUID
    medicine_id: UUID
    quantity: int
    status: TransferStatus
    created_at: datetime
    recommended_by: RecommendedBy = RecommendedBy.MANUAL
    created_by: UUID | None = None
    distance_km: float | None = None
    transportation_cost: float | None = None
    expiry_prevented_value: float | None = None
    completed_at: datetime | None = None
