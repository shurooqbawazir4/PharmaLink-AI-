"""Milestone B's `ExpiryRiskScorer` implementation: a documented heuristic,
not a trained model. Compares how long the batch would take to sell
through at its recent consumption rate (`days_to_exhaust`) against how long
it has left (`days_to_expiry`) — replaced by `MLExpiryScorer` behind the
same `domain.expiry.scorer.ExpiryRiskScorer` interface in Milestone C.
"""

from __future__ import annotations

from datetime import date

from app.domain.expiry.scorer import ExpiryRiskResult
from app.domain.inventory.entities import InventoryBatch

# Naive scorers can't back their estimate with a model, so they report a
# fixed, deliberately unimpressive confidence — real confidence comes from
# Milestone C's trained model.
_HEURISTIC_CONFIDENCE = 0.4
_NO_SIGNAL_CONFIDENCE = 0.2


class NaiveExpiryScorer:
    def score(self, batch: InventoryBatch, avg_daily_consumption: float) -> ExpiryRiskResult:
        days_to_expiry = max((batch.expiry_date - date.today()).days, 0)

        if batch.current_stock <= 0:
            probability, confidence = 0.0, 1.0
        elif days_to_expiry == 0:
            probability, confidence = 1.0, 1.0
        elif avg_daily_consumption <= 0:
            # No consumption signal at all in the trailing window — can't
            # confirm this batch moves before it expires. Treat short-dated
            # stock as high risk, longer-dated stock as merely uncertain.
            probability = 0.9 if days_to_expiry < 90 else 0.5
            confidence = _NO_SIGNAL_CONFIDENCE
        else:
            days_to_exhaust = batch.current_stock / avg_daily_consumption
            if days_to_exhaust <= days_to_expiry:
                # On pace to sell through comfortably before expiry.
                probability = max(0.0, 0.15 * (days_to_exhaust / days_to_expiry))
            else:
                # Still holding stock by the time it expires, proportional
                # to how far past expiry the sell-through would run.
                overhang = (days_to_exhaust - days_to_expiry) / days_to_exhaust
                probability = min(1.0, 0.5 + overhang * 0.5)
            confidence = _HEURISTIC_CONFIDENCE

        financial_loss = batch.current_stock * batch.unit_cost_at_receipt * probability
        return ExpiryRiskResult(
            probability=round(probability, 3),
            estimated_financial_loss=round(financial_loss, 2),
            confidence_score=confidence,
        )
