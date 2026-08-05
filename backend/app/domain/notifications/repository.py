"""Repository interface for the notifications (alerts) module."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.notifications.entities import Alert
from app.domain.shared.enums import AlertSeverity, AlertType


class AlertRepository(Protocol):
    async def get_by_id(self, alert_id: UUID) -> Alert | None: ...

    async def list(
        self,
        *,
        hospital_id: UUID | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        is_resolved: bool | None = None,
    ) -> list[Alert]: ...

    async def create(self, alert: Alert) -> Alert: ...

    async def update(self, alert: Alert) -> Alert: ...
