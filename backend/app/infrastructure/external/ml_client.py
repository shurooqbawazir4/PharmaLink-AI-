"""Adapts domain data into what `/ml` expects (plain pandas DataFrames)
and back — the one place in the backend that touches pandas/LightGBM-
shaped data directly. See docs/architecture.md for the `/backend` <->
`/ml` boundary this implements.

Imports `forecasting` as a top-level package (not `ml.forecasting`) —
`/ml`'s `pyproject.toml` discovers `forecasting`/`optimization` as
independent top-level packages rather than nesting them under an `ml`
namespace package, which would need a `ml/ml/` directory layout to work
with setuptools. A naming detail, not a boundary violation: `/ml` is still
installed and imported as its own dependency, never the reverse.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd
from forecasting.interface import Forecaster, ForecastResult
from forecasting.lightgbm_forecaster import LightGBMForecaster

_TRAINING_FRAME_COLUMNS = ["hospital_id", "medicine_id", "date", "quantity", "flu_activity_index"]


class MLForecastClient:
    """Wraps a `Forecaster`, training it lazily (once) on first use and
    caching it for the lifetime of the process — see
    `core/di.py::get_ml_forecast_client` for the singleton wiring."""

    def __init__(self, forecaster: Forecaster | None = None) -> None:
        self._forecaster: Forecaster = forecaster or LightGBMForecaster()
        self._is_trained = False

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    def ensure_trained(self, training_rows: Sequence[Mapping[str, object]]) -> None:
        if self._is_trained:
            return
        training_frame = pd.DataFrame(training_rows, columns=_TRAINING_FRAME_COLUMNS)
        self._forecaster.fit(training_frame)
        self._is_trained = True

    def forecast(
        self,
        *,
        hospital_id: str,
        medicine_id: str,
        horizon_days: int,
        recent_rows: Sequence[Mapping[str, object]],
    ) -> ForecastResult:
        if not self._is_trained:
            msg = "MLForecastClient.forecast called before ensure_trained()"
            raise RuntimeError(msg)
        recent_frame = pd.DataFrame(recent_rows, columns=_TRAINING_FRAME_COLUMNS)
        return self._forecaster.predict(
            hospital_id=hospital_id,
            medicine_id=medicine_id,
            horizon_days=horizon_days,
            recent_history=recent_frame,
        )
