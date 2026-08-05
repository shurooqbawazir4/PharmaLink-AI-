"""Repository interface for the transfers module."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.shared.enums import TransferStatus
from app.domain.transfers.entities import Transfer


class TransferRepository(Protocol):
    async def get_by_id(self, transfer_id: UUID) -> Transfer | None: ...

    async def list_transfers(
        self,
        *,
        hospital_id: UUID | None = None,
        status: TransferStatus | None = None,
        medicine_id: UUID | None = None,
    ) -> list[Transfer]:
        """`hospital_id` matches either source or destination — from a given
        hospital's point of view, both directions are relevant."""
        ...

    async def create(self, transfer: Transfer) -> Transfer: ...

    async def update(self, transfer: Transfer) -> Transfer: ...
