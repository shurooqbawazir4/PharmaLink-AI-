"""SQLAlchemy implementation of `app.domain.expiry.repository.ExpiryRiskRepository`.

`expiry_risk` is a hypertable that accumulates one row per evaluation, not
one row per batch — every read here narrows to the *latest* evaluation per
`inventory_id` via a `MAX(evaluated_at)` subquery join.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Subquery, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.expiry.entities import ExpiryRiskRecord
from app.infrastructure.db.models import ExpiryRiskModel, InventoryModel


class SQLAlchemyExpiryRiskRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def _latest_per_batch_subquery(self) -> Subquery:
        return (
            select(
                ExpiryRiskModel.inventory_id,
                func.max(ExpiryRiskModel.evaluated_at).label("latest_evaluated_at"),
            )
            .group_by(ExpiryRiskModel.inventory_id)
            .subquery()
        )

    async def get_latest_for_inventory(self, inventory_id: UUID) -> ExpiryRiskRecord | None:
        stmt = (
            select(ExpiryRiskModel)
            .where(ExpiryRiskModel.inventory_id == inventory_id)
            .order_by(ExpiryRiskModel.evaluated_at.desc())
            .limit(1)
        )
        model = await self._db.scalar(stmt)
        return self._to_entity(model) if model else None

    async def list_high_risk(
        self, *, threshold: float = 0.5, hospital_id: UUID | None = None
    ) -> list[ExpiryRiskRecord]:
        latest = self._latest_per_batch_subquery()
        stmt = (
            select(ExpiryRiskModel)
            .join(
                latest,
                and_(
                    ExpiryRiskModel.inventory_id == latest.c.inventory_id,
                    ExpiryRiskModel.evaluated_at == latest.c.latest_evaluated_at,
                ),
            )
            .where(ExpiryRiskModel.probability_expires_before_use >= threshold)
        )
        if hospital_id is not None:
            stmt = stmt.join(
                InventoryModel, InventoryModel.id == ExpiryRiskModel.inventory_id
            ).where(InventoryModel.hospital_id == hospital_id)
        stmt = stmt.order_by(ExpiryRiskModel.probability_expires_before_use.desc())
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    async def create(self, record: ExpiryRiskRecord) -> ExpiryRiskRecord:
        model = ExpiryRiskModel(
            id=record.id,
            evaluated_at=record.evaluated_at,
            inventory_id=record.inventory_id,
            probability_expires_before_use=record.probability_expires_before_use,
            estimated_financial_loss=record.estimated_financial_loss,
            confidence_score=record.confidence_score,
        )
        self._db.add(model)
        await self._db.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: ExpiryRiskModel) -> ExpiryRiskRecord:
        return ExpiryRiskRecord(
            id=model.id,
            inventory_id=model.inventory_id,
            probability_expires_before_use=model.probability_expires_before_use,
            estimated_financial_loss=model.estimated_financial_loss,
            confidence_score=model.confidence_score,
            evaluated_at=model.evaluated_at,
        )
