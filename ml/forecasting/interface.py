"""The forecasting contract every `Forecaster` implementation satisfies.

No FastAPI/SQLAlchemy imports anywhere in `/ml` — see docs/architecture.md
for the `/backend` <-> `/ml` boundary. The backend's
`infrastructure/external/ml_client.py` is the only place that adapts
between domain data and this package's plain pandas/dataclass shapes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass(slots=True, frozen=True)
class ForecastResult:
    predicted_demand: float
    """Total predicted units over the requested horizon (daily rate x horizon_days)."""
    confidence_low: float
    confidence_high: float
    model_used: str
    """'lightgbm' or 'chronos' — stored on the Forecasts row as-is."""


class Forecaster(Protocol):
    def fit(self, training_frame: pd.DataFrame) -> None:
        """Train on pooled history across every (hospital, medicine) pair.
        `training_frame` columns: hospital_id, medicine_id, date, quantity,
        flu_activity_index (nullable)."""
        ...

    def predict(
        self,
        *,
        hospital_id: str,
        medicine_id: str,
        horizon_days: int,
        recent_history: pd.DataFrame,
    ) -> ForecastResult:
        """Forecast total demand over `horizon_days`, using `recent_history`
        (that one pair's trailing rows, same columns as `training_frame`
        minus hospital_id/medicine_id) to derive the latest lag/rolling
        features. Raises if `fit` hasn't been called yet."""
        ...
