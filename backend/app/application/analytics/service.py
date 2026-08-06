"""Analytics use cases: cross-table KPI reporting.

Deliberately the one service that depends on `AsyncSession` directly
instead of a repository interface — these are aggregate reporting queries
across many tables, not single-entity CRUD, so forcing them through
per-entity repositories would be the wrong abstraction (see
docs/architecture.md). Milestone B computed only what's derivable without
ML; Milestone D adds the Sustainability-page numbers (see below).
`forecast_accuracy` is deliberately still not computed — forecasts predict
forward from "now" and the seeded historical consumption data has no
elapsed time to compare against yet, so a real accuracy figure doesn't
exist. The frontend renders that one tile as an explicit "not enough data
yet" state rather than being given a fabricated number.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.shared.enums import (
    InventoryChangeReason,
    PurchaseOrderStatus,
    TransferStatus,
)
from app.infrastructure.db.models import (
    AlertModel,
    ConsumptionModel,
    InventoryHistoryModel,
    InventoryModel,
    PurchaseOrderModel,
    TransferModel,
)

_TURNOVER_WINDOW_DAYS = 90
_PATIENT_IMPACT_WINDOW_DAYS = 90

# Illustrative estimate, not a measured value — a rough per-dose
# manufacturing-footprint ballpark (pharmaceutical carbon-footprint
# literature commonly cites low-single-digit kgCO2e per dose/unit
# depending on drug class). Stated here, in one place, so the
# Sustainability page can label it honestly rather than imply precision
# it doesn't have. Same documentation standard as the Chronos stub.
_CO2_KG_PER_UNIT_ESTIMATE = 1.2


@dataclass(slots=True, frozen=True)
class KPISummary:
    medicine_waste_units: int
    medicine_waste_value: float
    transfers_completed: int
    transfers_cancelled: int
    transfer_success_rate: float | None
    procurement_spend: float
    procurement_orders_count: int
    stockout_count: int
    inventory_turnover_ratio: float | None
    alerts_by_severity: dict[str, int] = field(default_factory=dict)
    alerts_unresolved_count: int = 0
    # --- Sustainability-page numbers (Milestone D) ---------------------------
    expiry_value_prevented: float = 0.0
    medicine_units_redistributed: int = 0
    co2_saved_kg_estimate: float = 0.0
    patients_impacted_count: int = 0


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_kpi_summary(self, hospital_id: UUID | None = None) -> KPISummary:
        waste_units, waste_value = await self._medicine_waste(hospital_id)
        completed, cancelled = await self._transfer_outcomes(hospital_id)
        total_terminal = completed + cancelled
        success_rate = completed / total_terminal if total_terminal > 0 else None
        spend, orders_count = await self._procurement_spend(hospital_id)
        stockout_count = await self._stockout_count(hospital_id)
        turnover_ratio = await self._inventory_turnover_ratio(hospital_id)
        alerts_by_severity, alerts_unresolved = await self._alert_summary(hospital_id)
        value_prevented, units_redistributed = await self._sustainability_impact(hospital_id)
        patients_impacted = await self._patients_impacted_count(hospital_id)

        return KPISummary(
            medicine_waste_units=waste_units,
            medicine_waste_value=waste_value,
            transfers_completed=completed,
            transfers_cancelled=cancelled,
            transfer_success_rate=success_rate,
            procurement_spend=spend,
            procurement_orders_count=orders_count,
            stockout_count=stockout_count,
            inventory_turnover_ratio=turnover_ratio,
            alerts_by_severity=alerts_by_severity,
            alerts_unresolved_count=alerts_unresolved,
            expiry_value_prevented=value_prevented,
            medicine_units_redistributed=units_redistributed,
            co2_saved_kg_estimate=round(units_redistributed * _CO2_KG_PER_UNIT_ESTIMATE, 1),
            patients_impacted_count=patients_impacted,
        )

    async def _medicine_waste(self, hospital_id: UUID | None) -> tuple[int, float]:
        # Consumption/write-off change_qty is stored negative (see
        # InventoryRepository.record_change) — negate for a positive total.
        stmt = (
            select(
                func.coalesce(func.sum(-InventoryHistoryModel.change_qty), 0),
                func.coalesce(
                    func.sum(
                        -InventoryHistoryModel.change_qty * InventoryModel.unit_cost_at_receipt
                    ),
                    0.0,
                ),
            )
            .join(InventoryModel, InventoryModel.id == InventoryHistoryModel.inventory_id)
            .where(InventoryHistoryModel.reason == InventoryChangeReason.EXPIRY_WRITEOFF)
        )
        if hospital_id is not None:
            stmt = stmt.where(InventoryHistoryModel.hospital_id == hospital_id)
        units, value = (await self._db.execute(stmt)).one()
        return int(units), round(float(value), 2)

    async def _transfer_outcomes(self, hospital_id: UUID | None) -> tuple[int, int]:
        stmt = select(TransferModel.status, func.count()).where(
            TransferModel.status.in_([TransferStatus.COMPLETED, TransferStatus.CANCELLED])
        )
        if hospital_id is not None:
            stmt = stmt.where(
                or_(
                    TransferModel.source_hospital_id == hospital_id,
                    TransferModel.destination_hospital_id == hospital_id,
                )
            )
        stmt = stmt.group_by(TransferModel.status)
        counts: dict[TransferStatus, int] = {
            status: count for status, count in await self._db.execute(stmt)
        }
        return (
            counts.get(TransferStatus.COMPLETED, 0),
            counts.get(TransferStatus.CANCELLED, 0),
        )

    async def _procurement_spend(self, hospital_id: UUID | None) -> tuple[float, int]:
        active_statuses = [PurchaseOrderStatus.ORDERED, PurchaseOrderStatus.RECEIVED]
        stmt = select(
            func.coalesce(func.sum(PurchaseOrderModel.total_cost), 0.0), func.count()
        ).where(PurchaseOrderModel.status.in_(active_statuses))
        if hospital_id is not None:
            stmt = stmt.where(PurchaseOrderModel.hospital_id == hospital_id)
        spend, count = (await self._db.execute(stmt)).one()
        return round(float(spend), 2), int(count)

    async def _stockout_count(self, hospital_id: UUID | None) -> int:
        stmt = (
            select(func.count())
            .select_from(InventoryModel)
            .where(InventoryModel.current_stock == 0)
        )
        if hospital_id is not None:
            stmt = stmt.where(InventoryModel.hospital_id == hospital_id)
        return int((await self._db.scalar(stmt)) or 0)

    async def _inventory_turnover_ratio(self, hospital_id: UUID | None) -> float | None:
        """Rough turnover proxy: units consumed in the trailing window over
        current total stock — a simplified stand-in for a true
        cost-of-goods-sold/average-inventory-value ratio."""
        since = datetime.now(UTC) - timedelta(days=_TURNOVER_WINDOW_DAYS)
        consumed_stmt = select(func.coalesce(func.sum(-InventoryHistoryModel.change_qty), 0)).where(
            InventoryHistoryModel.reason == InventoryChangeReason.CONSUMPTION,
            InventoryHistoryModel.recorded_at >= since,
        )
        stock_stmt = select(func.coalesce(func.sum(InventoryModel.current_stock), 0))
        if hospital_id is not None:
            consumed_stmt = consumed_stmt.where(InventoryHistoryModel.hospital_id == hospital_id)
            stock_stmt = stock_stmt.where(InventoryModel.hospital_id == hospital_id)

        consumed = (await self._db.scalar(consumed_stmt)) or 0
        current_total_stock = (await self._db.scalar(stock_stmt)) or 0
        if current_total_stock <= 0:
            return None
        return round(consumed / current_total_stock, 3)

    async def _sustainability_impact(self, hospital_id: UUID | None) -> tuple[float, int]:
        """Real redistribution impact of completed transfers: dollar value of
        near-expiry stock saved (`Transfer.expiry_prevented_value`, populated
        by `TransferService.complete` when a transfer draws from a batch
        close to expiring) and total units moved, the basis for the
        Sustainability page's CO2-saved estimate."""
        stmt = select(
            func.coalesce(func.sum(TransferModel.expiry_prevented_value), 0.0),
            func.coalesce(func.sum(TransferModel.quantity), 0),
        ).where(TransferModel.status == TransferStatus.COMPLETED)
        if hospital_id is not None:
            stmt = stmt.where(
                or_(
                    TransferModel.source_hospital_id == hospital_id,
                    TransferModel.destination_hospital_id == hospital_id,
                )
            )
        value_prevented, units_redistributed = (await self._db.execute(stmt)).one()
        return round(float(value_prevented), 2), int(units_redistributed)

    async def _patients_impacted_count(self, hospital_id: UUID | None) -> int:
        """Distinct patients with a recorded consumption event in the
        trailing window — how many patients this hospital's (or the
        network's) medicine activity actually touched. `patient_id` is a
        nullable FK on `consumption` (not every recorded dose is linked to
        a specific patient), so this counts only the linked subset."""
        since = datetime.now(UTC) - timedelta(days=_PATIENT_IMPACT_WINDOW_DAYS)
        stmt = select(func.count(func.distinct(ConsumptionModel.patient_id))).where(
            ConsumptionModel.patient_id.is_not(None),
            ConsumptionModel.consumed_at >= since,
        )
        if hospital_id is not None:
            stmt = stmt.where(ConsumptionModel.hospital_id == hospital_id)
        return int((await self._db.scalar(stmt)) or 0)

    async def _alert_summary(self, hospital_id: UUID | None) -> tuple[dict[str, int], int]:
        stmt = select(AlertModel.severity, AlertModel.is_resolved, func.count()).group_by(
            AlertModel.severity, AlertModel.is_resolved
        )
        if hospital_id is not None:
            stmt = stmt.where(AlertModel.hospital_id == hospital_id)

        by_severity: dict[str, int] = defaultdict(int)
        unresolved = 0
        for severity, is_resolved, count in await self._db.execute(stmt):
            by_severity[severity.value] += count
            if not is_resolved:
                unresolved += count
        return dict(by_severity), unresolved
