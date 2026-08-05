"""Milestone B's `ProcurementRecommender` implementation: a standard
reorder-point/par-level formula, not an optimizer. Reorders once stock
would run out before a new order could arrive (`reorder_point`), ordering
back up to a small buffer beyond that (`par_level`) — replaced by
Milestone C's OR-Tools-informed recommender behind the same
`domain.procurement.recommender.ProcurementRecommender` interface.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.domain.procurement.entities import Supplier
from app.domain.procurement.recommender import PurchaseRecommendation

# Order enough to cover lead time *plus* this many extra days, so the next
# reorder doesn't fire again immediately after this one arrives.
_SAFETY_BUFFER_DAYS = 14


class NaiveProcurementRecommender:
    def recommend(
        self,
        *,
        current_stock: int,
        safety_stock: int,
        avg_daily_consumption: float,
        unit_cost: float,
        supplier: Supplier,
    ) -> PurchaseRecommendation | None:
        if avg_daily_consumption <= 0:
            # No recent demand signal to size an order against.
            return None

        reorder_point = avg_daily_consumption * supplier.lead_time_days + safety_stock
        if current_stock >= reorder_point:
            return None

        par_level = (
            avg_daily_consumption * (supplier.lead_time_days + _SAFETY_BUFFER_DAYS) + safety_stock
        )
        quantity = round(par_level - current_stock)
        if quantity <= 0:
            return None

        return PurchaseRecommendation(
            quantity=quantity,
            unit_cost=unit_cost,
            expected_delivery_date=date.today() + timedelta(days=supplier.lead_time_days),
        )
