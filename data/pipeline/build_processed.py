#!/usr/bin/env python3
"""Turn the raw FluView weekly series into a smooth day-of-year seasonality
climatology — the real-world signal `data/synthetic/generate.py` scales
synthetic hospital demand against.

Why a climatology (average by day-of-year across all fetched years) rather
than the raw weekly series directly: Delphi's data has real reporting lag
(recent weeks can be ~90 days behind), so the most recent portion of the
synthetic generator's trailing window has no raw data to align to. A
day-of-year seasonal profile — "respiratory illness activity typically
looks like *this* in mid-January vs. mid-July" — is a defensible use of
real data for any date, including ones newer than what's been reported.

Usage: python build_processed.py  (run after fetch_fluview.py)
Output: data/processed/flu_seasonality_by_doy.csv
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

RAW_PATH = Path(__file__).resolve().parent.parent / "raw" / "fluview" / "ili_activity.csv"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "processed" / "flu_seasonality_by_doy.csv"
SMOOTHING_WINDOW_DAYS = 14


def _epiweek_to_day_of_year(epiweek: int) -> int:
    """Approximate mapping (CDC MMWR week -> ~date -> day-of-year). Only the
    *seasonal shape* matters here, not exact week boundaries — see the
    module docstring."""
    year, week = divmod(epiweek, 100)
    approx_date = date(year, 1, 1) + timedelta(weeks=week - 1)
    return approx_date.timetuple().tm_yday


def main() -> None:
    if not RAW_PATH.exists():
        print(f"{RAW_PATH} not found — run fetch_fluview.py first.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(RAW_PATH)
    df = df.dropna(subset=["wili"])
    if df.empty:
        print("No usable rows in the raw FluView data.", file=sys.stderr)
        sys.exit(1)

    df["day_of_year"] = df["epiweek"].astype(int).map(_epiweek_to_day_of_year)

    # Min-max normalize wili (weighted ILI %) to a 0-1 index across the
    # whole fetched history, then average by day-of-year (the climatology).
    wili_min, wili_max = df["wili"].min(), df["wili"].max()
    df["flu_index"] = (df["wili"] - wili_min) / (wili_max - wili_min)
    climatology = df.groupby("day_of_year")["flu_index"].mean()

    # Fill any day-of-year gaps (weeks don't divide evenly into 366 days)
    # and circularly smooth so the curve doesn't jump week-to-week.
    full_range = climatology.reindex(range(1, 367))
    full_range = full_range.interpolate(limit_direction="both")
    padded = pd.concat([full_range.tail(SMOOTHING_WINDOW_DAYS), full_range, full_range.head(SMOOTHING_WINDOW_DAYS)])
    smoothed = padded.rolling(SMOOTHING_WINDOW_DAYS, center=True, min_periods=1).mean()
    smoothed = smoothed.iloc[SMOOTHING_WINDOW_DAYS : SMOOTHING_WINDOW_DAYS + 366]

    out = pd.DataFrame(
        {"day_of_year": np.arange(1, 367), "flu_index": smoothed.to_numpy().round(4)}
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(out)}-day seasonality climatology -> {OUTPUT_PATH}")
    print(f"  flu_index range: {out['flu_index'].min():.3f} - {out['flu_index'].max():.3f}")


if __name__ == "__main__":
    main()
