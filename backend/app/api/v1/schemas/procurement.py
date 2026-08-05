"""Pydantic v2 request/response models for the procurement endpoints
(suppliers + purchase orders)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.shared.enums import PurchaseOrderStatus, RecommendedBy


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    lead_time_days: int = Field(gt=0)
    reliability_score: float = Field(default=1.0, ge=0.0, le=1.0)
    contact_email: str | None = Field(default=None, max_length=255)


class SupplierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    contact_email: str | None
    lead_time_days: int
    reliability_score: float
    is_active: bool
    created_at: datetime


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hospital_id: UUID
    medicine_id: UUID
    supplier_id: UUID
    quantity: int
    status: PurchaseOrderStatus
    recommended_by: RecommendedBy
    unit_cost: float
    total_cost: float
    created_at: datetime
    expected_delivery_date: date | None


class PurchaseOrderReceiveRequest(BaseModel):
    batch_number: str = Field(min_length=1, max_length=100)
    expiry_date: date
