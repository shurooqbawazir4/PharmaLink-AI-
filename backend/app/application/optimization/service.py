"""Network-wide transfer optimization for one medicine at a time.

Depends on `InventoryRepository`, `HospitalRepository`, `ForecastService`,
and `TransferService` — reused directly, so an AI-recommended transfer is
created exactly the same way a human-proposed one is (same validation,
same haversine cost), just tagged `recommended_by=RecommendedBy.AI` and
chosen from a network-wide optimization run instead of one hospital's
manual judgment. See `ml/optimization/transfer_optimizer.py` for the
actual OR-Tools solve, and docs/architecture.md for why this is a service-
only module (no new table — its output *is* proposed Transfers + alerts).
"""

from __future__ import annotations

from uuid import UUID

from optimization.transfer_optimizer import HospitalState, solve_network_transfers

from app.application.forecast.service import ForecastService
from app.application.notifications.service import NotificationService
from app.application.transfers.service import TransferService
from app.domain.hospitals.repository import HospitalRepository
from app.domain.inventory.repository import InventoryRepository
from app.domain.shared.enums import AlertSeverity, AlertType, RecommendedBy
from app.domain.transfers.entities import Transfer

# The demand window the optimizer projects stock against — independent of
# whatever horizon a given pair's last forecast happened to be generated
# at (predicted_demand is linearly rescaled to this window below).
_OPTIMIZATION_HORIZON_DAYS = 30


class OptimizationService:
    def __init__(
        self,
        inventory_repository: InventoryRepository,
        hospital_repository: HospitalRepository,
        forecast_service: ForecastService,
        transfer_service: TransferService,
        notification_service: NotificationService | None = None,
    ) -> None:
        self._inventory = inventory_repository
        self._hospitals = hospital_repository
        self._forecasts = forecast_service
        self._transfers = transfer_service
        self._notifications = notification_service

    async def optimize_network(self, medicine_id: UUID) -> list[Transfer]:
        states = await self._build_hospital_states(medicine_id)
        recommendations = solve_network_transfers(states)

        created_transfers: list[Transfer] = []
        for recommendation in recommendations:
            transfer = await self._transfers.propose(
                source_hospital_id=UUID(recommendation.source_hospital_id),
                destination_hospital_id=UUID(recommendation.destination_hospital_id),
                medicine_id=medicine_id,
                quantity=recommendation.quantity,
                recommended_by=RecommendedBy.AI,
            )
            created_transfers.append(transfer)

            if self._notifications is not None:
                await self._notifications.create_alert(
                    hospital_id=transfer.destination_hospital_id,
                    medicine_id=medicine_id,
                    alert_type=AlertType.TRANSFER_SUGGESTED,
                    severity=AlertSeverity.INFO,
                    message=(
                        f"AI recommends transferring {recommendation.quantity} units from a "
                        f"nearby hospital ({recommendation.distance_km:.0f} km) to cover "
                        "projected demand."
                    ),
                )
        return created_transfers

    async def _build_hospital_states(self, medicine_id: UUID) -> list[HospitalState]:
        # Only hospitals with an established stocking relationship for this
        # medicine are considered — a brand-new rollout to a hospital that's
        # never stocked it goes through Procurement, not this optimizer.
        hospitals = await self._hospitals.list(is_active=True)
        states: list[HospitalState] = []
        for hospital in hospitals:
            batches = await self._inventory.list_batches(
                hospital_id=hospital.id, medicine_id=medicine_id
            )
            if not batches:
                continue

            current_stock = sum(batch.current_stock for batch in batches)
            safety_stock = sum(batch.safety_stock for batch in batches)
            forecasted_demand = await self._forecasted_demand(hospital.id, medicine_id)

            states.append(
                HospitalState(
                    hospital_id=str(hospital.id),
                    current_stock=current_stock,
                    safety_stock=safety_stock,
                    forecasted_demand=forecasted_demand,
                    latitude=hospital.latitude,
                    longitude=hospital.longitude,
                )
            )
        return states

    async def _forecasted_demand(self, hospital_id: UUID, medicine_id: UUID) -> float:
        forecast = await self._forecasts.get_latest(hospital_id, medicine_id)
        if forecast is not None and forecast.horizon_days > 0:
            return forecast.predicted_demand * (_OPTIMIZATION_HORIZON_DAYS / forecast.horizon_days)
        daily_rate = await self._inventory.average_daily_consumption(hospital_id, medicine_id)
        return daily_rate * _OPTIMIZATION_HORIZON_DAYS
