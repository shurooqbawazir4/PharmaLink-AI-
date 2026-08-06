"""Repository interface for the forecast module.

`get_training_data`/`get_recent_history` are bulk historical reads for
feeding `/ml`, not single-entity CRUD — the same sanctioned exception
`AnalyticsService` established for cross-table aggregate reads (see
docs/architecture.md).
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, TypedDict
from uuid import UUID

from app.domain.forecast.entities import Forecast


class ConsumptionRow(TypedDict):
    hospital_id: str
    medicine_id: str
    date: date
    quantity: int
    flu_activity_index: float | None


class ForecastRepository(Protocol):
    async def get_latest(self, hospital_id: UUID, medicine_id: UUID) -> Forecast | None: ...

    async def list_forecasts(
        self,
        *,
        hospital_id: UUID | None = None,
        medicine_id: UUID | None = None,
    ) -> list[Forecast]: ...

    async def create(self, forecast: Forecast) -> Forecast: ...

    async def get_training_data(self) -> list[ConsumptionRow]:
        """Every (hospital, medicine, day) consumption total across the
        whole network, joined with that day's real flu-activity index —
        the pooled training set `/ml`'s forecaster fits once per process."""
        ...

    async def get_recent_history(
        self, hospital_id: UUID, medicine_id: UUID, *, since: date
    ) -> list[ConsumptionRow]:
        """One pair's trailing daily consumption — used to derive the
        latest lag/rolling features at prediction time."""
        ...
