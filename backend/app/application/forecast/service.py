"""Forecast use cases. `generate()` is an explicit "run the model now"
action (mirrors Expiry's `evaluate_batch`/Procurement's
`recommend_for_hospital`); `get_daily_rate()` is the read-only lookup
Expiry/Procurement call into for a forecast-derived demand signal,
falling back to their own historical-average signal when nothing's been
generated yet for that pair — see docs/architecture.md.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from app.domain.forecast.entities import Forecast
from app.domain.forecast.repository import ForecastRepository
from app.domain.shared.enums import ForecastModelType
from app.infrastructure.external.ml_client import MLForecastClient

# How far back "recent history" reaches when deriving prediction-time lag/
# rolling features — must comfortably cover the longest rolling window
# ml/forecasting/features.py computes (30 days) plus slack.
_RECENT_HISTORY_DAYS = 90


class ForecastService:
    def __init__(
        self, forecast_repository: ForecastRepository, ml_client: MLForecastClient
    ) -> None:
        self._forecasts = forecast_repository
        self._ml = ml_client

    async def generate(
        self, hospital_id: UUID, medicine_id: UUID, horizon_days: int = 30
    ) -> Forecast:
        if not self._ml.is_trained:
            training_rows = await self._forecasts.get_training_data()
            self._ml.ensure_trained(list(training_rows))

        since = date.today() - timedelta(days=_RECENT_HISTORY_DAYS)
        recent_rows = await self._forecasts.get_recent_history(
            hospital_id, medicine_id, since=since
        )
        result = self._ml.forecast(
            hospital_id=str(hospital_id),
            medicine_id=str(medicine_id),
            horizon_days=horizon_days,
            recent_rows=list(recent_rows),
        )

        forecast = Forecast(
            id=uuid4(),
            hospital_id=hospital_id,
            medicine_id=medicine_id,
            horizon_days=horizon_days,
            model_used=ForecastModelType(result.model_used),
            predicted_demand=result.predicted_demand,
            confidence_low=result.confidence_low,
            confidence_high=result.confidence_high,
            generated_at=datetime.now(UTC),
        )
        return await self._forecasts.create(forecast)

    async def get_latest(self, hospital_id: UUID, medicine_id: UUID) -> Forecast | None:
        return await self._forecasts.get_latest(hospital_id, medicine_id)

    async def list_forecasts(
        self, *, hospital_id: UUID | None = None, medicine_id: UUID | None = None
    ) -> list[Forecast]:
        return await self._forecasts.list_forecasts(
            hospital_id=hospital_id, medicine_id=medicine_id
        )

    async def get_daily_rate(self, hospital_id: UUID, medicine_id: UUID) -> float | None:
        """The latest forecast's predicted_demand, normalized to a daily
        rate — `None` if nothing's been generated for this pair yet, which
        callers should treat as "fall back to the historical average"."""
        latest = await self.get_latest(hospital_id, medicine_id)
        if latest is None or latest.horizon_days <= 0:
            return None
        return latest.predicted_demand / latest.horizon_days
