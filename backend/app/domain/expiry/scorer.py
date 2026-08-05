"""The pluggable expiry-risk scoring interface.

Milestone B ships `infrastructure/external/naive_expiry_scorer.py` behind
this `Protocol`; Milestone C adds an ML-backed implementation and swaps it
in `core/di.py` — the same Chronos/LightGBM-style fallback pattern already
used for Forecast, applied one milestone early so Expiry is demoable now
rather than waiting on the ML pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.inventory.entities import InventoryBatch


@dataclass(slots=True, frozen=True)
class ExpiryRiskResult:
    probability: float
    """Probability this batch expires before it's fully consumed, in [0, 1]."""
    estimated_financial_loss: float
    """Expected write-off value if it does — `current_stock * unit_cost * probability`."""
    confidence_score: float
    """How much to trust this estimate, in [0, 1] — naive scorers report a
    fixed, conservative value; a trained model reports something real."""


class ExpiryRiskScorer(Protocol):
    def score(self, batch: InventoryBatch, avg_daily_consumption: float) -> ExpiryRiskResult: ...
