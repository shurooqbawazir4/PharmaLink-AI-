"""Enums shared between domain entities and ORM models.

Centralized here (rather than duplicated per module) so the same value set
backs both the SQLAlchemy `Enum` columns in
`app/infrastructure/db/models.py` and any domain/application logic that
branches on them — one definition, no drift.
"""

from __future__ import annotations

from enum import StrEnum


class InventoryChangeReason(StrEnum):
    RECEIPT = "receipt"
    CONSUMPTION = "consumption"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    EXPIRY_WRITEOFF = "expiry_writeoff"
    ADJUSTMENT = "adjustment"


class TransferStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_TRANSIT = "in_transit"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ForecastModelType(StrEnum):
    """Which ML model produced a forecast row — not to be confused with the
    `ForecastModel` SQLAlchemy ORM class in `infrastructure/db/models.py`."""

    CHRONOS = "chronos"
    LIGHTGBM = "lightgbm"


class PurchaseOrderStatus(StrEnum):
    RECOMMENDED = "recommended"
    APPROVED = "approved"
    ORDERED = "ordered"
    RECEIVED = "received"
    CANCELLED = "cancelled"


class RecommendedBy(StrEnum):
    AI = "ai"
    MANUAL = "manual"


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(StrEnum):
    SHORTAGE_RISK = "shortage_risk"
    EXPIRY_RISK = "expiry_risk"
    LOW_STOCK = "low_stock"
    TRANSFER_SUGGESTED = "transfer_suggested"


class HospitalType(StrEnum):
    GENERAL = "general"
    SPECIALTY = "specialty"
    TEACHING = "teaching"
    CLINIC = "clinic"
