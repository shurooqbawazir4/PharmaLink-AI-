"""Pydantic v2 response models for the alerts (notifications) endpoints.

Alerts are raised internally by other services, not created directly
through the API — see `application/notifications/service.py` — so there's
no `AlertCreate` schema, only read/resolve.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.shared.enums import AlertSeverity, AlertType


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hospital_id: UUID
    medicine_id: UUID | None
    severity: AlertSeverity
    type: AlertType
    message: str
    is_resolved: bool
    created_at: datetime
