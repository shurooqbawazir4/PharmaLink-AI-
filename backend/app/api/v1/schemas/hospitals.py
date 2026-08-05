"""Pydantic v2 request/response models for the hospitals endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.shared.enums import HospitalType


class HospitalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=20)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    city: str = Field(min_length=1, max_length=120)
    region: str = Field(min_length=1, max_length=120)
    bed_capacity: int = Field(gt=0)
    type: HospitalType


class HospitalUpdateOccupancy(BaseModel):
    occupancy_rate: float = Field(ge=0.0, le=1.0)


class HospitalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
