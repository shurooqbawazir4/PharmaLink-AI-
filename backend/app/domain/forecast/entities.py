"""Forecast domain entity — plain dataclass, no ORM/framework imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.shared.enums import ForecastModelType


@dataclass(slots=True, frozen=True)
class Forecast:
    id: UUID
    hospital_id: UUID
    medicine_id: UUID
    horizon_days: int
    model_used: ForecastModelType
    predicted_demand: float
    confidence_low: float
    confidence_high: float
    generated_at: datetime
