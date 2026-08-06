"""In-memory fake repositories used by unit tests.

Each fake implements the corresponding domain `Protocol` exactly — this is
what lets `HospitalService`/`MedicineService` be tested with zero database,
zero Docker, and zero network I/O.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pandas as pd
from forecasting.interface import ForecastResult

from app.domain.expiry.entities import ExpiryRiskRecord
from app.domain.forecast.entities import Forecast
from app.domain.forecast.repository import ConsumptionRow
from app.domain.hospitals.entities import Hospital
from app.domain.inventory.entities import InventoryBatch, InventoryChange
from app.domain.medicines.entities import Medicine
from app.domain.notifications.entities import Alert
from app.domain.procurement.entities import PurchaseOrder, Supplier
from app.domain.shared.enums import (
    AlertSeverity,
    AlertType,
    InventoryChangeReason,
    PurchaseOrderStatus,
    TransferStatus,
)
from app.domain.transfers.entities import Transfer
from app.infrastructure.external.llm.provider import Message


class FakeHospitalRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Hospital] = {}

    async def get_by_id(self, hospital_id: UUID) -> Hospital | None:
        return self._by_id.get(hospital_id)

    async def get_by_code(self, code: str) -> Hospital | None:
        return next((h for h in self._by_id.values() if h.code == code), None)

    async def list(
        self, *, region: str | None = None, is_active: bool | None = True
    ) -> list[Hospital]:
        hospitals: list[Hospital] = list(self._by_id.values())
        if region is not None:
            hospitals = [h for h in hospitals if h.region == region]
        if is_active is not None:
            hospitals = [h for h in hospitals if h.is_active == is_active]
        return sorted(hospitals, key=lambda h: h.name)

    async def create(self, hospital: Hospital) -> Hospital:
        self._by_id[hospital.id] = hospital
        return hospital

    async def update(self, hospital: Hospital) -> Hospital:
        self._by_id[hospital.id] = hospital
        return hospital


class FakeMedicineRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Medicine] = {}

    async def get_by_id(self, medicine_id: UUID) -> Medicine | None:
        return self._by_id.get(medicine_id)

    async def list(
        self, *, category: str | None = None, is_active: bool | None = True
    ) -> list[Medicine]:
        medicines: list[Medicine] = list(self._by_id.values())
        if category is not None:
            medicines = [m for m in medicines if m.category == category]
        if is_active is not None:
            medicines = [m for m in medicines if m.is_active == is_active]
        return sorted(medicines, key=lambda m: m.name)

    async def create(self, medicine: Medicine) -> Medicine:
        self._by_id[medicine.id] = medicine
        return medicine

    async def update(self, medicine: Medicine) -> Medicine:
        self._by_id[medicine.id] = medicine
        return medicine


class FakeAlertRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Alert] = {}

    async def get_by_id(self, alert_id: UUID) -> Alert | None:
        return self._by_id.get(alert_id)

    async def list(
        self,
        *,
        hospital_id: UUID | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        is_resolved: bool | None = None,
    ) -> list[Alert]:
        alerts: list[Alert] = list(self._by_id.values())
        if hospital_id is not None:
            alerts = [a for a in alerts if a.hospital_id == hospital_id]
        if severity is not None:
            alerts = [a for a in alerts if a.severity == severity]
        if alert_type is not None:
            alerts = [a for a in alerts if a.type == alert_type]
        if is_resolved is not None:
            alerts = [a for a in alerts if a.is_resolved == is_resolved]
        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    async def create(self, alert: Alert) -> Alert:
        self._by_id[alert.id] = alert
        return alert

    async def update(self, alert: Alert) -> Alert:
        self._by_id[alert.id] = alert
        return alert


class FakeInventoryRepository:
    """Mirrors `SQLAlchemyInventoryRepository`'s behavior closely enough for
    unit tests: `average_daily_consumption` sums all recorded consumption
    history for the pair (no time-windowing — tests control what's added,
    so the window itself isn't exercised here)."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, InventoryBatch] = {}
        self._history: list[tuple[UUID, UUID, int, InventoryChangeReason]] = []

    async def get_by_id(self, inventory_id: UUID) -> InventoryBatch | None:
        return self._by_id.get(inventory_id)

    async def list_batches(
        self,
        *,
        hospital_id: UUID | None = None,
        medicine_id: UUID | None = None,
        expiring_within_days: int | None = None,
        below_safety_stock: bool | None = None,
    ) -> list[InventoryBatch]:
        batches: list[InventoryBatch] = list(self._by_id.values())
        if hospital_id is not None:
            batches = [b for b in batches if b.hospital_id == hospital_id]
        if medicine_id is not None:
            batches = [b for b in batches if b.medicine_id == medicine_id]
        if below_safety_stock:
            batches = [b for b in batches if b.current_stock < b.safety_stock]
        return sorted(batches, key=lambda b: b.expiry_date)

    async def list_fefo(self, hospital_id: UUID, medicine_id: UUID) -> list[InventoryBatch]:
        batches = [
            b
            for b in self._by_id.values()
            if b.hospital_id == hospital_id and b.medicine_id == medicine_id and b.current_stock > 0
        ]
        return sorted(batches, key=lambda b: b.expiry_date)

    async def create(
        self,
        batch: InventoryBatch,
        *,
        reason: InventoryChangeReason = InventoryChangeReason.RECEIPT,
    ) -> InventoryBatch:
        self._by_id[batch.id] = batch
        self._history.append((batch.hospital_id, batch.medicine_id, batch.current_stock, reason))
        return batch

    async def record_change(
        self, inventory_id: UUID, change_qty: int, reason: InventoryChangeReason
    ) -> InventoryChange:
        batch = self._by_id[inventory_id]
        batch.current_stock += change_qty
        self._history.append((batch.hospital_id, batch.medicine_id, change_qty, reason))
        return InventoryChange(
            batch=batch, change_qty=change_qty, reason=reason, recorded_at=datetime.now(UTC)
        )

    async def average_daily_consumption(
        self, hospital_id: UUID, medicine_id: UUID, window_days: int = 30
    ) -> float:
        total = -sum(
            qty
            for hid, mid, qty, reason in self._history
            if hid == hospital_id
            and mid == medicine_id
            and reason == InventoryChangeReason.CONSUMPTION
        )
        return max(total, 0) / window_days


class FakeTransferRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Transfer] = {}

    async def get_by_id(self, transfer_id: UUID) -> Transfer | None:
        return self._by_id.get(transfer_id)

    async def list_transfers(
        self,
        *,
        hospital_id: UUID | None = None,
        status: TransferStatus | None = None,
        medicine_id: UUID | None = None,
    ) -> list[Transfer]:
        transfers: list[Transfer] = list(self._by_id.values())
        if hospital_id is not None:
            transfers = [
                t
                for t in transfers
                if hospital_id in (t.source_hospital_id, t.destination_hospital_id)
            ]
        if status is not None:
            transfers = [t for t in transfers if t.status == status]
        if medicine_id is not None:
            transfers = [t for t in transfers if t.medicine_id == medicine_id]
        return sorted(transfers, key=lambda t: t.created_at, reverse=True)

    async def create(self, transfer: Transfer) -> Transfer:
        self._by_id[transfer.id] = transfer
        return transfer

    async def update(self, transfer: Transfer) -> Transfer:
        self._by_id[transfer.id] = transfer
        return transfer


class FakeExpiryRiskRepository:
    def __init__(self) -> None:
        self._records: list[ExpiryRiskRecord] = []

    async def get_latest_for_inventory(self, inventory_id: UUID) -> ExpiryRiskRecord | None:
        matches = [r for r in self._records if r.inventory_id == inventory_id]
        return max(matches, key=lambda r: r.evaluated_at) if matches else None

    async def list_high_risk(
        self, *, threshold: float = 0.5, hospital_id: UUID | None = None
    ) -> list[ExpiryRiskRecord]:
        # hospital_id filtering is skipped in the fake (would need an
        # inventory-batch join); unit tests exercise this unfiltered.
        return [r for r in self._records if r.probability_expires_before_use >= threshold]

    async def create(self, record: ExpiryRiskRecord) -> ExpiryRiskRecord:
        self._records.append(record)
        return record


class FakeSupplierRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, Supplier] = {}

    async def get_by_id(self, supplier_id: UUID) -> Supplier | None:
        return self._by_id.get(supplier_id)

    async def list_suppliers(self, *, is_active: bool | None = True) -> list[Supplier]:
        suppliers: list[Supplier] = list(self._by_id.values())
        if is_active is not None:
            suppliers = [s for s in suppliers if s.is_active == is_active]
        return sorted(suppliers, key=lambda s: s.reliability_score, reverse=True)

    async def create(self, supplier: Supplier) -> Supplier:
        self._by_id[supplier.id] = supplier
        return supplier

    async def update(self, supplier: Supplier) -> Supplier:
        self._by_id[supplier.id] = supplier
        return supplier


class FakePurchaseOrderRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, PurchaseOrder] = {}

    async def get_by_id(self, order_id: UUID) -> PurchaseOrder | None:
        return self._by_id.get(order_id)

    async def list_orders(
        self,
        *,
        hospital_id: UUID | None = None,
        status: PurchaseOrderStatus | None = None,
        medicine_id: UUID | None = None,
    ) -> list[PurchaseOrder]:
        orders: list[PurchaseOrder] = list(self._by_id.values())
        if hospital_id is not None:
            orders = [o for o in orders if o.hospital_id == hospital_id]
        if status is not None:
            orders = [o for o in orders if o.status == status]
        if medicine_id is not None:
            orders = [o for o in orders if o.medicine_id == medicine_id]
        return sorted(orders, key=lambda o: o.created_at, reverse=True)

    async def create(self, order: PurchaseOrder) -> PurchaseOrder:
        self._by_id[order.id] = order
        return order

    async def update(self, order: PurchaseOrder) -> PurchaseOrder:
        self._by_id[order.id] = order
        return order


def make_inventory_batch(
    *,
    hospital_id: UUID | None = None,
    medicine_id: UUID | None = None,
    current_stock: int = 100,
    safety_stock: int = 10,
    expiry_date: date | None = None,
    unit_cost_at_receipt: float = 5.0,
    batch_number: str = "BATCH-1",
) -> InventoryBatch:
    """Test helper: a fully-populated `InventoryBatch` with sane defaults,
    so tests only have to specify the fields they actually care about."""
    return InventoryBatch(
        id=uuid4(),
        hospital_id=hospital_id or uuid4(),
        medicine_id=medicine_id or uuid4(),
        batch_number=batch_number,
        current_stock=current_stock,
        safety_stock=safety_stock,
        expiry_date=expiry_date or date.today() + timedelta(days=180),
        unit_cost_at_receipt=unit_cost_at_receipt,
        created_at=datetime.now(UTC),
    )


def make_supplier(*, lead_time_days: int = 7, reliability_score: float = 1.0) -> Supplier:
    return Supplier(
        id=uuid4(),
        name="Test Supplier",
        lead_time_days=lead_time_days,
        reliability_score=reliability_score,
        is_active=True,
        created_at=datetime.now(UTC),
    )


class FakeForecastRepository:
    """`training_data`/`recent_history_by_pair` are plain public attributes
    tests populate directly — this repository has no DB behind it to seed,
    just in-memory lists a test wires up before calling the service."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, Forecast] = {}
        self.training_data: list[ConsumptionRow] = []
        self.recent_history_by_pair: dict[tuple[UUID, UUID], list[ConsumptionRow]] = {}

    async def get_latest(self, hospital_id: UUID, medicine_id: UUID) -> Forecast | None:
        matches = [
            f
            for f in self._by_id.values()
            if f.hospital_id == hospital_id and f.medicine_id == medicine_id
        ]
        return max(matches, key=lambda f: f.generated_at) if matches else None

    async def list_forecasts(
        self, *, hospital_id: UUID | None = None, medicine_id: UUID | None = None
    ) -> list[Forecast]:
        forecasts: list[Forecast] = list(self._by_id.values())
        if hospital_id is not None:
            forecasts = [f for f in forecasts if f.hospital_id == hospital_id]
        if medicine_id is not None:
            forecasts = [f for f in forecasts if f.medicine_id == medicine_id]
        return forecasts

    async def create(self, forecast: Forecast) -> Forecast:
        self._by_id[forecast.id] = forecast
        return forecast

    async def get_training_data(self) -> list[ConsumptionRow]:
        return self.training_data

    async def get_recent_history(
        self, hospital_id: UUID, medicine_id: UUID, *, since: date
    ) -> list[ConsumptionRow]:
        return self.recent_history_by_pair.get((hospital_id, medicine_id), [])


class FakeForecaster:
    """A `forecasting.interface.Forecaster` that returns a fixed daily rate
    — injected into a *real* `MLForecastClient` so its train-once caching
    behavior is still exercised for real, without needing real LightGBM
    training data volume (see docs/architecture.md's ml_client boundary)."""

    def __init__(self, daily_rate: float = 10.0) -> None:
        self.daily_rate = daily_rate
        self.fit_call_count = 0

    def fit(self, training_frame: pd.DataFrame) -> None:
        self.fit_call_count += 1

    def predict(
        self,
        *,
        hospital_id: str,
        medicine_id: str,
        horizon_days: int,
        recent_history: pd.DataFrame,
    ) -> ForecastResult:
        return ForecastResult(
            predicted_demand=self.daily_rate * horizon_days,
            confidence_low=self.daily_rate * horizon_days * 0.8,
            confidence_high=self.daily_rate * horizon_days * 1.2,
            model_used="lightgbm",
        )


class FakeLLMProvider:
    """No live Groq calls in the automated suite — returns a fixed
    response and records what it was asked, so tests can assert the right
    grounding data made it into the prompt without needing a real key."""

    def __init__(self, response: str = "This is a canned explanation.") -> None:
        self.response = response
        self.last_system_prompt: str | None = None
        self.last_messages: list[Message] = []

    async def complete(self, *, system_prompt: str, messages: list[Message]) -> str:
        self.last_system_prompt = system_prompt
        self.last_messages = messages
        return self.response
