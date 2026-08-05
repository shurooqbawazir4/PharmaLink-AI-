"""Notifications use cases.

`create_alert` is designed to be called by *other* services (Inventory
raises `low_stock`, Expiry raises `expiry_risk`, ...) as well as directly
through the API in principle — there's no separate "internal" vs "external"
codepath, just one service method every caller shares. Delivery is
persist-and-query only for now: no email/webhook channel yet (a deliberate
Milestone B stub, not an oversight — see docs/architecture.md).
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.notifications.entities import Alert
from app.domain.notifications.exceptions import AlertNotFoundError
from app.domain.notifications.repository import AlertRepository
from app.domain.shared.enums import AlertSeverity, AlertType


class NotificationService:
    def __init__(self, alert_repository: AlertRepository) -> None:
        self._alerts = alert_repository

    async def create_alert(
        self,
        *,
        hospital_id: UUID,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        medicine_id: UUID | None = None,
    ) -> Alert:
        alert = Alert(
            id=uuid4(),
            hospital_id=hospital_id,
            medicine_id=medicine_id,
            severity=severity,
            type=alert_type,
            message=message,
            is_resolved=False,
            created_at=datetime.now(UTC),
        )
        return await self._alerts.create(alert)

    async def get(self, alert_id: UUID) -> Alert:
        alert = await self._alerts.get_by_id(alert_id)
        if alert is None:
            raise AlertNotFoundError(str(alert_id))
        return alert

    async def list(
        self,
        *,
        hospital_id: UUID | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        is_resolved: bool | None = None,
    ) -> list[Alert]:
        return await self._alerts.list(
            hospital_id=hospital_id,
            severity=severity,
            alert_type=alert_type,
            is_resolved=is_resolved,
        )

    async def resolve(self, alert_id: UUID) -> Alert:
        alert = await self.get(alert_id)
        alert.is_resolved = True
        return await self._alerts.update(alert)
