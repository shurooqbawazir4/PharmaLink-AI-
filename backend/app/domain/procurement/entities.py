"""Procurement domain entities — plain dataclasses, no ORM/framework imports.

Suppliers are managed as part of Procurement (the original module spec
lists 11 backend modules and Suppliers isn't a separate one — it's the
catalogue Procurement's purchase orders reference).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.domain.shared.enums import PurchaseOrderStatus, RecommendedBy


@dataclass(slots=True)
class Supplier:
    id: UUID
    name: str
    lead_time_days: int
    reliability_score: float
    is_active: bool
    created_at: datetime
    contact_email: str | None = None


@dataclass(slots=True)
class PurchaseOrder:
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
    expected_delivery_date: date | None = None
