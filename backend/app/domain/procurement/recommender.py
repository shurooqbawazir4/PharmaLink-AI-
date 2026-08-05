"""The pluggable procurement-recommendation interface.

Milestone B ships `infrastructure/external/naive_procurement_recommender.py`
behind this `Protocol` — the same naive-now/ML-later pattern as
`domain/expiry/scorer.py`. Milestone C's OR-Tools-informed recommender
swaps in behind the same interface. Supplier *selection* stays a service-
layer concern (see `application/procurement/service.py`) in both — this
`Protocol` answers "should we reorder, and how much/when," not "from whom."
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.domain.procurement.entities import Supplier


@dataclass(slots=True, frozen=True)
class PurchaseRecommendation:
    quantity: int
    unit_cost: float
    expected_delivery_date: date | None


class ProcurementRecommender(Protocol):
    def recommend(
        self,
        *,
        current_stock: int,
        safety_stock: int,
        avg_daily_consumption: float,
        unit_cost: float,
        supplier: Supplier,
    ) -> PurchaseRecommendation | None:
        """Return a recommendation, or `None` if no reorder is needed right now."""
        ...
