"""Pydantic v2 response model for the analytics/KPI endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KPISummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    medicine_waste_units: int
    medicine_waste_value: float
    transfers_completed: int
    transfers_cancelled: int
    transfer_success_rate: float | None
    procurement_spend: float
    procurement_orders_count: int
    stockout_count: int
    inventory_turnover_ratio: float | None
    alerts_by_severity: dict[str, int]
    alerts_unresolved_count: int
