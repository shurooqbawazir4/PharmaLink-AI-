"""SQLAlchemy implementation of `app.domain.transfers.repository.TransferRepository`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.shared.enums import TransferStatus
from app.domain.transfers.entities import Transfer
from app.infrastructure.db.models import TransferModel


class SQLAlchemyTransferRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, transfer_id: UUID) -> Transfer | None:
        model = await self._db.get(TransferModel, transfer_id)
        return self._to_entity(model) if model else None

    async def list_transfers(
        self,
        *,
        hospital_id: UUID | None = None,
        status: TransferStatus | None = None,
        medicine_id: UUID | None = None,
    ) -> list[Transfer]:
        stmt = select(TransferModel)
        if hospital_id is not None:
            stmt = stmt.where(
                or_(
                    TransferModel.source_hospital_id == hospital_id,
                    TransferModel.destination_hospital_id == hospital_id,
                )
            )
        if status is not None:
            stmt = stmt.where(TransferModel.status == status)
        if medicine_id is not None:
            stmt = stmt.where(TransferModel.medicine_id == medicine_id)
        stmt = stmt.order_by(TransferModel.created_at.desc())
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    async def create(self, transfer: Transfer) -> Transfer:
        model = TransferModel(
            id=transfer.id,
            source_hospital_id=transfer.source_hospital_id,
            destination_hospital_id=transfer.destination_hospital_id,
            medicine_id=transfer.medicine_id,
            quantity=transfer.quantity,
            status=transfer.status,
            distance_km=transfer.distance_km,
            transportation_cost=transfer.transportation_cost,
            expiry_prevented_value=transfer.expiry_prevented_value,
            created_by=transfer.created_by,
            completed_at=transfer.completed_at,
        )
        self._db.add(model)
        await self._db.flush()
        return self._to_entity(model)

    async def update(self, transfer: Transfer) -> Transfer:
        model = await self._db.get(TransferModel, transfer.id)
        if model is None:
            msg = f"Transfer {transfer.id} not found for update"
            raise ValueError(msg)
        model.status = transfer.status
        model.expiry_prevented_value = transfer.expiry_prevented_value
        model.completed_at = transfer.completed_at
        await self._db.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: TransferModel) -> Transfer:
        return Transfer(
            id=model.id,
            source_hospital_id=model.source_hospital_id,
            destination_hospital_id=model.destination_hospital_id,
            medicine_id=model.medicine_id,
            quantity=model.quantity,
            status=model.status,
            created_at=model.created_at,
            created_by=model.created_by,
            distance_km=model.distance_km,
            transportation_cost=model.transportation_cost,
            expiry_prevented_value=model.expiry_prevented_value,
            completed_at=model.completed_at,
        )
