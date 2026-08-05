"""Pydantic v2 request/response models for the medicines endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MedicineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    generic_name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=30)
    unit_cost: float = Field(gt=0)
    atc_code: str | None = Field(default=None, max_length=20)
    requires_refrigeration: bool = False
    is_controlled: bool = False


class MedicineUpdateCost(BaseModel):
    unit_cost: float = Field(gt=0)


class MedicineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
