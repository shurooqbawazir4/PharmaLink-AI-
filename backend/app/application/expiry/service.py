"""Expiry-risk use cases. Depends on `InventoryRepository` (for the batch
and its consumption signal) and the pluggable `ExpiryRiskScorer` — see
`domain/expiry/scorer.py` for why that's an interface, not a concrete class.

Milestone C addition: given a `ForecastService`, the consumption-rate
signal fed to the scorer prefers a real forecast (seasonality/trend-aware)
over the Milestone B historical average, falling back to the average when
no forecast has been generated yet for that pair — see
docs/architecture.md for why this is a service-layer change rather than a
new `ExpiryRiskScorer` implementation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application.forecast.service import ForecastService
from app.application.notifications.service import NotificationService
from app.domain.expiry.entities import ExpiryRiskRecord
from app.domain.expiry.repository import ExpiryRiskRepository
from app.domain.expiry.scorer import ExpiryRiskScorer
from app.domain.inventory.exceptions import InventoryBatchNotFoundError
from app.domain.inventory.repository import InventoryRepository
from app.domain.shared.enums import AlertSeverity, AlertType

# At or above this probability, a `low`/`warning` alert becomes `critical`.
_CRITICAL_RISK_THRESHOLD = 0.85
# Below this probability, evaluating a batch doesn't raise an alert at all.
_ALERT_RISK_THRESHOLD = 0.5


class ExpiryService:
    def __init__(
        self,
        expiry_repository: ExpiryRiskRepository,
        inventory_repository: InventoryRepository,
        scorer: ExpiryRiskScorer,
        notification_service: NotificationService | None = None,
        forecast_service: ForecastService | None = None,
    ) -> None:
        self._expiry = expiry_repository
        self._inventory = inventory_repository
        self._scorer = scorer
        self._notifications = notification_service
        self._forecasts = forecast_service

    async def _daily_consumption_signal(self, hospital_id: UUID, medicine_id: UUID) -> float:
        if self._forecasts is not None:
            forecast_rate = await self._forecasts.get_daily_rate(hospital_id, medicine_id)
            if forecast_rate is not None:
                return forecast_rate
        return await self._inventory.average_daily_consumption(hospital_id, medicine_id)

    async def evaluate_batch(self, inventory_id: UUID) -> ExpiryRiskRecord:
        batch = await self._inventory.get_by_id(inventory_id)
        if batch is None:
            raise InventoryBatchNotFoundError(str(inventory_id))

        avg_daily_consumption = await self._daily_consumption_signal(
            batch.hospital_id, batch.medicine_id
        )
        result = self._scorer.score(batch, avg_daily_consumption)

        record = ExpiryRiskRecord(
            id=uuid4(),
            inventory_id=inventory_id,
            probability_expires_before_use=result.probability,
            estimated_financial_loss=result.estimated_financial_loss,
            confidence_score=result.confidence_score,
            evaluated_at=datetime.now(UTC),
        )
        created = await self._expiry.create(record)

        if self._notifications is not None and result.probability >= _ALERT_RISK_THRESHOLD:
            severity = (
                AlertSeverity.CRITICAL
                if result.probability >= _CRITICAL_RISK_THRESHOLD
                else AlertSeverity.WARNING
            )
            await self._notifications.create_alert(
                hospital_id=batch.hospital_id,
                medicine_id=batch.medicine_id,
                alert_type=AlertType.EXPIRY_RISK,
                severity=severity,
                message=(
                    f"Batch {batch.batch_number} has a "
                    f"{result.probability:.0%} chance of expiring unused "
                    f"(est. ${result.estimated_financial_loss:,.2f} at risk)."
                ),
            )
        return created

    async def evaluate_hospital(self, hospital_id: UUID) -> list[ExpiryRiskRecord]:
        batches = await self._inventory.list_batches(hospital_id=hospital_id)
        return [await self.evaluate_batch(batch.id) for batch in batches]

    async def get_latest_for_inventory(self, inventory_id: UUID) -> ExpiryRiskRecord | None:
        return await self._expiry.get_latest_for_inventory(inventory_id)

    async def list_high_risk(
        self, *, threshold: float = 0.5, hospital_id: UUID | None = None
    ) -> list[ExpiryRiskRecord]:
        return await self._expiry.list_high_risk(threshold=threshold, hospital_id=hospital_id)
