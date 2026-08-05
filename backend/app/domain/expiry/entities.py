"""Expiry-risk domain entity — plain dataclass, no ORM/framework imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class ExpiryRiskRecord:
    id: UUID
    inventory_id: UUID
    probability_expires_before_use: float
    estimated_financial_loss: float
    confidence_score: float
    evaluated_at: datetime
