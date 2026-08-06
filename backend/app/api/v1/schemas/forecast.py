"""Pydantic v2 response model for the forecast endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.shared.enums import ForecastModelType


class ForecastRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hospital_id: UUID
    medicine_id: UUID
    horizon_days: int
    model_used: ForecastModelType
    predicted_demand: float
    confidence_low: float
    confidence_high: float
    generated_at: datetime
