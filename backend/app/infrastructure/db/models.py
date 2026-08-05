"""SQLAlchemy ORM models — the single source of truth for the DB schema.

Every table from the approved design lives here, even though only
Auth/Hospitals/Medicines have repository + service + API code in this
milestone; the rest are schema-only until Milestone B wires up their
modules. This means the initial Alembic migration (and every later one)
only ever needs to diff against this one file.

Naming convention: ORM classes are suffixed `Model` (e.g. `HospitalModel`)
to keep them visually distinct from the framework-free domain entities of
the same concept (e.g. `app.domain.hospitals.entities.Hospital`).

TimescaleDB hypertables (append-only, time-indexed, high-volume) use a
composite primary key `(id, <time column>)`, which is what TimescaleDB
requires when a hypertable has a primary key at all — everything else uses
a plain single-column UUID primary key.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.shared.enums import (
    AlertSeverity,
    AlertType,
    ForecastModelType,
    HospitalType,
    InventoryChangeReason,
    PurchaseOrderStatus,
    RecommendedBy,
    TransferStatus,
)
from app.infrastructure.db.base import Base, TimestampMixin, UUIDPKMixin

# Native JSONB on Postgres (indexable, more efficient); falls back to plain
# JSON on any other dialect (e.g. SQLite in tests) — one column definition
# that works everywhere.
_JSONVariant = JSON().with_variant(JSONB, "postgresql")


def _fk(table_column: str, *, nullable: bool = False) -> Mapped[uuid.UUID]:
    """Shorthand for an indexed UUID foreign key column."""
    return mapped_column(
        Uuid(as_uuid=True), ForeignKey(table_column), nullable=nullable, index=True
    )


# ---------------------------------------------------------------------------
# Auth: roles & users
# ---------------------------------------------------------------------------


class RoleModel(UUIDPKMixin, Base):
    """RBAC role. Permissions are a flat JSONB string list (e.g. ["hospitals:write"],
    or ["*"] for admin) so new permissions don't require a migration."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    permissions: Mapped[list[str]] = mapped_column(_JSONVariant, nullable=False, default=list)

    users: Mapped[list[UserModel]] = relationship(back_populates="role")


class UserModel(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = _fk("roles.id")
    hospital_id: Mapped[uuid.UUID | None] = _fk("hospitals.id", nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    role: Mapped[RoleModel] = relationship(back_populates="users")
    hospital: Mapped[HospitalModel | None] = relationship(back_populates="users")


# ---------------------------------------------------------------------------
# Hospitals & suppliers
# ---------------------------------------------------------------------------


class HospitalModel(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "hospitals"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    region: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    bed_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    occupancy_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    type: Mapped[HospitalType] = mapped_column(
        Enum(HospitalType, name="hospital_type"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    users: Mapped[list[UserModel]] = relationship(back_populates="hospital")


class SupplierModel(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# ---------------------------------------------------------------------------
# Medicines & inventory
# ---------------------------------------------------------------------------


class MedicineModel(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "medicines"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    generic_name: Mapped[str] = mapped_column(String(255), nullable=False)
    atc_code: Mapped[str | None] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    requires_refrigeration: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_controlled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class InventoryModel(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "inventory"
    __table_args__ = ({"comment": "One row per physical batch of a medicine at a hospital."},)

    hospital_id: Mapped[uuid.UUID] = _fk("hospitals.id")
    medicine_id: Mapped[uuid.UUID] = _fk("medicines.id")
    batch_number: Mapped[str] = mapped_column(String(100), nullable=False)
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safety_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_location: Mapped[str | None] = mapped_column(String(120))
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    manufactured_date: Mapped[date | None] = mapped_column(Date)
    supplier_id: Mapped[uuid.UUID | None] = _fk("suppliers.id", nullable=True)
    unit_cost_at_receipt: Mapped[float] = mapped_column(Float, nullable=False)


class InventoryHistoryModel(Base):
    """Hypertable: every stock-changing event for an inventory batch."""

    __tablename__ = "inventory_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False, index=True
    )
    inventory_id: Mapped[uuid.UUID] = _fk("inventory.id")
    hospital_id: Mapped[uuid.UUID] = _fk("hospitals.id")
    medicine_id: Mapped[uuid.UUID] = _fk("medicines.id")
    change_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[InventoryChangeReason] = mapped_column(
        Enum(InventoryChangeReason, name="inventory_change_reason"), nullable=False
    )


# ---------------------------------------------------------------------------
# Demand signal: consumption, patients, weather
# ---------------------------------------------------------------------------


class PatientModel(UUIDPKMixin, TimestampMixin, Base):
    """Deliberately minimal & de-identified — synthetic/aggregate admission
    context for demand forecasting, not a real clinical record."""

    __tablename__ = "patients"

    hospital_id: Mapped[uuid.UUID] = _fk("hospitals.id")
    anonymized_ref: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    age_band: Mapped[str] = mapped_column(String(20), nullable=False)
    admission_date: Mapped[date] = mapped_column(Date, nullable=False)
    discharge_date: Mapped[date | None] = mapped_column(Date)
    primary_diagnosis_code: Mapped[str | None] = mapped_column(String(20))


class ConsumptionModel(Base):
    """Hypertable: the core demand-forecasting signal — medicine units used."""

    __tablename__ = "consumption"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    consumed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False, index=True
    )
    hospital_id: Mapped[uuid.UUID] = _fk("hospitals.id")
    medicine_id: Mapped[uuid.UUID] = _fk("medicines.id")
    patient_id: Mapped[uuid.UUID | None] = _fk("patients.id", nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))


class WeatherModel(Base):
    """Hypertable: regional weather + flu-activity index, a forecasting feature."""

    __tablename__ = "weather"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recorded_date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    flu_activity_index: Mapped[float | None] = mapped_column(Float)


# ---------------------------------------------------------------------------
# Transfers, forecasts, expiry risk
# ---------------------------------------------------------------------------


class TransferModel(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "transfers"

    source_hospital_id: Mapped[uuid.UUID] = _fk("hospitals.id")
    destination_hospital_id: Mapped[uuid.UUID] = _fk("hospitals.id")
    medicine_id: Mapped[uuid.UUID] = _fk("medicines.id")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, name="transfer_status"),
        nullable=False,
        default=TransferStatus.PROPOSED,
    )
    transportation_cost: Mapped[float | None] = mapped_column(Float)
    distance_km: Mapped[float | None] = mapped_column(Float)
    expiry_prevented_value: Mapped[float | None] = mapped_column(Float)
    created_by: Mapped[uuid.UUID | None] = _fk("users.id", nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ForecastModel(Base):
    """Hypertable: one row per (hospital, medicine, horizon) forecast run."""

    __tablename__ = "forecasts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False, index=True
    )
    hospital_id: Mapped[uuid.UUID] = _fk("hospitals.id")
    medicine_id: Mapped[uuid.UUID] = _fk("medicines.id")
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    model_used: Mapped[ForecastModelType] = mapped_column(
        Enum(ForecastModelType, name="forecast_model_type"), nullable=False
    )
    predicted_demand: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_low: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_high: Mapped[float] = mapped_column(Float, nullable=False)


class ExpiryRiskModel(Base):
    """Hypertable: point-in-time expiry-risk score for an inventory batch."""

    __tablename__ = "expiry_risk"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False, index=True
    )
    inventory_id: Mapped[uuid.UUID] = _fk("inventory.id")
    probability_expires_before_use: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_financial_loss: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)


# ---------------------------------------------------------------------------
# Procurement, alerts, audit
# ---------------------------------------------------------------------------


class PurchaseOrderModel(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "purchase_orders"

    hospital_id: Mapped[uuid.UUID] = _fk("hospitals.id")
    medicine_id: Mapped[uuid.UUID] = _fk("medicines.id")
    supplier_id: Mapped[uuid.UUID] = _fk("suppliers.id")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(PurchaseOrderStatus, name="purchase_order_status"),
        nullable=False,
        default=PurchaseOrderStatus.RECOMMENDED,
    )
    recommended_by: Mapped[RecommendedBy] = mapped_column(
        Enum(RecommendedBy, name="recommended_by"), nullable=False, default=RecommendedBy.AI
    )
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date)


class AlertModel(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    hospital_id: Mapped[uuid.UUID] = _fk("hospitals.id")
    medicine_id: Mapped[uuid.UUID | None] = _fk("medicines.id", nullable=True)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity"), nullable=False
    )
    type: Mapped[AlertType] = mapped_column(Enum(AlertType, name="alert_type"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AuditLogModel(Base):
    """Hypertable: append-only trail of every mutating API request."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = _fk("users.id", nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(60))
    event_metadata: Mapped[dict[str, object] | None] = mapped_column(_JSONVariant)
    ip_address: Mapped[str | None] = mapped_column(String(45))


# Tables converted to TimescaleDB hypertables by the initial Alembic
# migration — kept here as the one place that enumerates them, so the
# migration can `from app.infrastructure.db.models import HYPERTABLES`.
HYPERTABLES: dict[str, str] = {
    "inventory_history": "recorded_at",
    "consumption": "consumed_at",
    "weather": "recorded_date",
    "forecasts": "generated_at",
    "expiry_risk": "evaluated_at",
    "audit_logs": "created_at",
}
