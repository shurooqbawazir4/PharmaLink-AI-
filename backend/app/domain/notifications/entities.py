"""Alert domain entity — plain dataclass, no ORM/framework imports.

Alerts are raised internally by other services (Inventory raises
`low_stock`, Expiry raises `expiry_risk`, ...) rather than created directly
by users through the API — see `application/notifications/service.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.shared.enums import AlertSeverity, AlertType


@dataclass(slots=True)
class Alert:
    id: UUID
    hospital_id: UUID
    severity: AlertSeverity
    type: AlertType
    message: str
    is_resolved: bool
    created_at: datetime
    medicine_id: UUID | None = None
