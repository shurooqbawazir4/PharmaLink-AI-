"""Feature engineering shared by training and prediction — one definition,
so the two paths can never silently drift apart.
"""

from __future__ import annotations

import pandas as pd

FEATURE_COLUMNS = [
    "lag_7",
    "lag_14",
    "rolling_mean_7",
    "rolling_mean_30",
    "day_of_week",
    "day_of_year",
    "flu_activity_index",
    "hospital_id",
    "medicine_id",
]
CATEGORICAL_COLUMNS = ["hospital_id", "medicine_id"]
TARGET_COLUMN = "quantity"


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """`df` needs columns: hospital_id, medicine_id, date, quantity,
    flu_activity_index (nullable). Returns a copy with the feature columns
    added; lag/rolling features are computed *within* each
    (hospital_id, medicine_id) group, sorted by date, so one pair's history
    never leaks into another's features."""
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values(["hospital_id", "medicine_id", "date"]).reset_index(drop=True)

    grouped_quantity = out.groupby(["hospital_id", "medicine_id"])[TARGET_COLUMN]
    out["lag_7"] = grouped_quantity.shift(7)
    out["lag_14"] = grouped_quantity.shift(14)
    # shift(1) before rolling so "recent" history never includes the day being predicted.
    out["rolling_mean_7"] = grouped_quantity.transform(lambda s: s.shift(1).rolling(7).mean())
    out["rolling_mean_30"] = grouped_quantity.transform(lambda s: s.shift(1).rolling(30).mean())

    out["day_of_week"] = out["date"].dt.dayofweek
    out["day_of_year"] = out["date"].dt.dayofyear
    out["flu_activity_index"] = out["flu_activity_index"].astype(float)

    for col in CATEGORICAL_COLUMNS:
        out[col] = out[col].astype(str).astype("category")

    return out


def latest_feature_row(
    recent_history: pd.DataFrame, *, hospital_id: str, medicine_id: str
) -> pd.DataFrame:
    """Build a single-row feature frame representing "today," from a pair's
    trailing raw history — for prediction, not training."""
    df = recent_history.copy()
    df["hospital_id"] = hospital_id
    df["medicine_id"] = medicine_id
    featured = add_features(df)
    return featured.tail(1)
