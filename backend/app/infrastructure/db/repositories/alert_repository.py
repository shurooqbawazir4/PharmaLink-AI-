"""SQLAlchemy implementation of `app.domain.notifications.repository.AlertRepository`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications.entities import Alert
from app.domain.shared.enums import AlertSeverity, AlertType
from app.infrastructure.db.models import AlertModel


class SQLAlchemyAlertRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, alert_id: UUID) -> Alert | None:
        model = await self._db.get(AlertModel, alert_id)
        return self._to_entity(model) if model else None

    async def list(
        self,
        *,
        hospital_id: UUID | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        is_resolved: bool | None = None,
    ) -> list[Alert]:
        stmt = select(AlertModel)
        if hospital_id is not None:
            stmt = stmt.where(AlertModel.hospital_id == hospital_id)
        if severity is not None:
            stmt = stmt.where(AlertModel.severity == severity)
        if alert_type is not None:
            stmt = stmt.where(AlertModel.type == alert_type)
        if is_resolved is not None:
            stmt = stmt.where(AlertModel.is_resolved == is_resolved)
        stmt = stmt.order_by(AlertModel.created_at.desc())
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    async def create(self, alert: Alert) -> Alert:
        model = AlertModel(
            id=alert.id,
            hospital_id=alert.hospital_id,
            medicine_id=alert.medicine_id,
            severity=alert.severity,
            type=alert.type,
            message=alert.message,
            is_resolved=alert.is_resolved,
        )
        self._db.add(model)
        await self._db.flush()
        return self._to_entity(model)

    async def update(self, alert: Alert) -> Alert:
        model = await self._db.get(AlertModel, alert.id)
        if model is None:
            msg = f"Alert {alert.id} not found for update"
            raise ValueError(msg)
        model.is_resolved = alert.is_resolved
        await self._db.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: AlertModel) -> Alert:
        return Alert(
            id=model.id,
            hospital_id=model.hospital_id,
            medicine_id=model.medicine_id,
            severity=model.severity,
            type=model.type,
            message=model.message,
            is_resolved=model.is_resolved,
            created_at=model.created_at,
        )
