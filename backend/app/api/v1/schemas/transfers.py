"""Pydantic v2 request/response models for the transfers endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.shared.enums import RecommendedBy, TransferStatus


class TransferProposeRequest(BaseModel):
    source_hospital_id: UUID
    destination_hospital_id: UUID
    medicine_id: UUID
    quantity: int = Field(gt=0)


class TransferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_hospital_id: UUID
    destination_hospital_id: UUID
    medicine_id: UUID
    quantity: int
    status: TransferStatus
    created_at: datetime
    recommended_by: RecommendedBy
    created_by: UUID | None
    distance_km: float | None
    transportation_cost: float | None
    expiry_prevented_value: float | None
    completed_at: datetime | None
