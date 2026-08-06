"""The documented, present-but-not-implemented Chronos swap point.

The original design says "Chronos first, LightGBM fallback." After
research, this milestone ships the reverse as the *working* default:
`chronos-forecasting` pulls in `torch` + `transformers` — multiple GB of
CPU-only dependencies and materially slower inference — for a demo
dataset (8 hospitals x 13 medicines, tabular, feature-rich: real FluView
seasonality, lag/rolling stats) that a well-featured LightGBM model
already fits well, not just cheaply. This class exists so the
`Forecaster` swap point promised by the architecture is real in code, not
just asserted — `core/di.py` could point at this instead of
`LightGBMForecaster` the moment someone wants to invest in wiring it up
for real (GPU inference, a foundation-model story for investors, etc.).
"""

from __future__ import annotations

import pandas as pd

from .interface import ForecastResult


class ChronosForecaster:
    def fit(self, training_frame: pd.DataFrame) -> None:
        raise NotImplementedError(
            "ChronosForecaster is a documented swap point, not implemented this "
            "milestone — see this module's docstring. Use LightGBMForecaster."
        )

    def predict(
        self,
        *,
        hospital_id: str,
        medicine_id: str,
        horizon_days: int,
        recent_history: pd.DataFrame,
    ) -> ForecastResult:
        raise NotImplementedError(
            "ChronosForecaster is a documented swap point, not implemented this "
            "milestone — see this module's docstring. Use LightGBMForecaster."
        )
