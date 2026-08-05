"""Alerts endpoints — read + resolve. Alerts themselves are raised internally
by other services (Inventory, Expiry, ...), never created directly here.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import CurrentUser, require_own_hospital_or_admin
from app.api.v1.schemas.notifications import AlertRead
from app.application.notifications.service import NotificationService
from app.core.di import get_notification_service
from app.domain.shared.enums import AlertSeverity, AlertType

router = APIRouter(prefix="/alerts", tags=["Notifications"])

NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


@router.get("/", response_model=list[AlertRead])
async def list_alerts(
    service: NotificationServiceDep,
    _current_user: CurrentUser,
    hospital_id: UUID | None = Query(default=None),
    severity: AlertSeverity | None = Query(default=None),
    type: AlertType | None = Query(default=None),  # noqa: A002 — matches the query param name
    is_resolved: bool | None = Query(default=None),
) -> list[AlertRead]:
    alerts = await service.list(
        hospital_id=hospital_id, severity=severity, alert_type=type, is_resolved=is_resolved
    )
    return [AlertRead.model_validate(alert) for alert in alerts]


@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert(
    alert_id: UUID, service: NotificationServiceDep, _current_user: CurrentUser
) -> AlertRead:
    alert = await service.get(alert_id)
    return AlertRead.model_validate(alert)


@router.patch("/{alert_id}/resolve", response_model=AlertRead)
async def resolve_alert(
    alert_id: UUID, service: NotificationServiceDep, current_user: CurrentUser
) -> AlertRead:
    alert = await service.get(alert_id)
    require_own_hospital_or_admin(current_user, alert.hospital_id)
    resolved = await service.resolve(alert_id)
    return AlertRead.model_validate(resolved)
