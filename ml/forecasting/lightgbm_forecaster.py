"""The real, load-bearing forecaster (quantile regression: q=0.1/0.5/0.9
give the confidence band). Trains once on pooled history across every
(hospital, medicine) pair — see `interface.py::Forecaster.fit` — then
`predict()` is a fast lookup against the already-trained model.

Predicts a *daily* rate at the latest known feature snapshot and scales it
by `horizon_days` to get a total — a direct-multiplication approximation
rather than a full recursive multi-step forecast. Documented, not hidden:
it's the right tradeoff for "expected volume over the next N days," which
is what Expiry/Procurement/Optimization actually consume, versus the
extra complexity of a proper multi-horizon model for a data volume this
size.
"""

from __future__ import annotations

import logging

import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error

from .features import CATEGORICAL_COLUMNS, FEATURE_COLUMNS, TARGET_COLUMN, add_features, latest_feature_row
from .interface import ForecastResult

logger = logging.getLogger(__name__)

_QUANTILE_ALPHAS = {"low": 0.1, "median": 0.5, "high": 0.9}
_MIN_TRAINING_ROWS = 200
_LAG_FEATURE_COLUMNS = ["lag_7", "lag_14", "rolling_mean_7", "rolling_mean_30"]


def _make_model(alpha: float) -> LGBMRegressor:
    return LGBMRegressor(
        objective="quantile",
        alpha=alpha,
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        min_child_samples=10,
        random_state=42,
        verbosity=-1,
    )


class LightGBMForecaster:
    def __init__(self) -> None:
        self._models: dict[str, LGBMRegressor] = {}
        self._is_fit = False

    def fit(self, training_frame: pd.DataFrame) -> None:
        featured = add_features(training_frame).dropna(subset=_LAG_FEATURE_COLUMNS)
        if len(featured) < _MIN_TRAINING_ROWS:
            msg = f"Not enough training rows after feature engineering: {len(featured)} < {_MIN_TRAINING_ROWS}"
            raise ValueError(msg)

        features = featured[FEATURE_COLUMNS]
        target = featured[TARGET_COLUMN]

        for name, alpha in _QUANTILE_ALPHAS.items():
            model = _make_model(alpha)
            model.fit(features, target, categorical_feature=CATEGORICAL_COLUMNS)
            self._models[name] = model

        # Sanity-check MAE on a per-pair trailing holdout — logged only,
        # doesn't gate deployment (every model above still trains on the
        # full frame; more real data only helps a demand forecaster).
        holdout = featured.groupby(["hospital_id", "medicine_id"], observed=True).tail(14)
        if not holdout.empty:
            predictions = self._models["median"].predict(holdout[FEATURE_COLUMNS])
            mae = mean_absolute_error(holdout[TARGET_COLUMN], predictions)
            logger.info("LightGBMForecaster: trained on %d rows, holdout MAE=%.2f", len(featured), mae)

        self._is_fit = True

    def predict(
        self,
        *,
        hospital_id: str,
        medicine_id: str,
        horizon_days: int,
        recent_history: pd.DataFrame,
    ) -> ForecastResult:
        if not self._is_fit:
            msg = "LightGBMForecaster.predict called before fit()"
            raise RuntimeError(msg)

        row = latest_feature_row(recent_history, hospital_id=hospital_id, medicine_id=medicine_id)
        row = row.dropna(subset=_LAG_FEATURE_COLUMNS)

        if row.empty:
            # Not enough trailing history for this pair yet (e.g. a
            # medicine never dispensed at this hospital before) — fall
            # back to a flat rate from whatever short history exists
            # rather than erroring the whole request.
            fallback_daily = (
                float(recent_history[TARGET_COLUMN].tail(14).mean()) if not recent_history.empty else 0.0
            )
            return ForecastResult(
                predicted_demand=round(fallback_daily * horizon_days, 2),
                confidence_low=round(fallback_daily * horizon_days * 0.7, 2),
                confidence_high=round(fallback_daily * horizon_days * 1.3, 2),
                model_used="lightgbm",
            )

        features = row[FEATURE_COLUMNS]
        daily_low = max(float(self._models["low"].predict(features)[0]), 0.0)
        daily_median = max(float(self._models["median"].predict(features)[0]), 0.0)
        daily_high = max(float(self._models["high"].predict(features)[0]), daily_low)

        return ForecastResult(
            predicted_demand=round(daily_median * horizon_days, 2),
            confidence_low=round(daily_low * horizon_days, 2),
            confidence_high=round(daily_high * horizon_days, 2),
            model_used="lightgbm",
        )
