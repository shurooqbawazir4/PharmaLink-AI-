"""Pydantic v2 request/response models for the inventory endpoints."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.shared.enums import InventoryChangeReason


class InventoryReceiveRequest(BaseModel):
    hospital_id: UUID
    medicine_id: UUID
    batch_number: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0)
    expiry_date: date
    unit_cost_at_receipt: float = Field(gt=0)
    safety_stock: int = Field(default=0, ge=0)
    storage_location: str | None = Field(default=None, max_length=120)
    manufactured_date: date | None = None
    supplier_id: UUID | None = None


class InventoryConsumeRequest(BaseModel):
    quantity: int = Field(gt=0)


class InventoryAdjustRequest(BaseModel):
    change_qty: int = Field(description="Positive to add stock, negative to remove it.")


class InventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hospital_id: UUID
    medicine_id: UUID
    batch_number: str
    current_stock: int
    safety_stock: int
    available_stock: int
    expiry_date: date
    unit_cost_at_receipt: float
    created_at: datetime
    storage_location: str | None
    manufactured_date: date | None
    supplier_id: UUID | None


class InventoryChangeRead(BaseModel):
    batch: InventoryRead
    change_qty: int
    reason: InventoryChangeReason
    recorded_at: datetime
