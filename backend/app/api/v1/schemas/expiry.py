"""Pydantic v2 response models for the expiry-risk endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExpiryRiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inventory_id: UUID
    probability_expires_before_use: float
    estimated_financial_loss: float
    confidence_score: float
    evaluated_at: datetime
