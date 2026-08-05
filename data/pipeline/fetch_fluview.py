#!/usr/bin/env python3
"""Fetch real weekly flu-activity data from the Delphi Epidata FluView API
(CMU) — the CDC's own FluView isn't a clean JSON API; this is the standard
no-auth path. See docs/architecture.md and the project's data pipeline
notes for why OpenPrescribing (the other originally-planned real source)
was dropped: it now sits behind Cloudflare bot-protection that blocks
automated access entirely (confirmed live — 403 on every request,
including the homepage, not just the API).

We fetch the *national* US series only. It's used purely as a real-world
*seasonality shape* (respiratory illness reliably peaks in winter) to drive
the synthetic hospital network's demand curve — not as a literal predictor
of activity in the synthetic hospitals' region. That distinction matters
and is documented again in data/synthetic/generate.py, where the signal is
actually consumed.

Usage: python fetch_fluview.py
Output: data/raw/fluview/ili_activity.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import requests

API_URL = "https://api.delphi.cmu.edu/epidata/fluview/"
# A broad static range rather than a computed "current epiweek" — Delphi's
# epiweek numbering (CDC MMWR weeks) is fiddly to compute correctly, and
# requesting extra weeks that don't exist yet is harmless (they're just
# absent from the response).
EPIWEEK_RANGE = "202001-202552"
REGION = "nat"

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "raw" / "fluview" / "ili_activity.csv"


def fetch() -> list[dict]:
    response = requests.get(
        API_URL, params={"regions": REGION, "epiweeks": EPIWEEK_RANGE}, timeout=30
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("result") != 1 or "epidata" not in payload:
        msg = f"Unexpected FluView API response: {payload.get('message', payload)}"
        raise RuntimeError(msg)
    return payload["epidata"]


def main() -> None:
    print(f"Fetching FluView ILI data ({REGION}, {EPIWEEK_RANGE}) ...")
    rows = fetch()
    if not rows:
        print("No rows returned — aborting without overwriting existing output.", file=sys.stderr)
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["region", "epiweek", "wili", "ili", "num_ili", "num_patients"]
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} weekly rows -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
