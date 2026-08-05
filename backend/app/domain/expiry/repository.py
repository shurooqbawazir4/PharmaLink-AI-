"""Repository interface for the expiry-risk module."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.expiry.entities import ExpiryRiskRecord


class ExpiryRiskRepository(Protocol):
    async def get_latest_for_inventory(self, inventory_id: UUID) -> ExpiryRiskRecord | None: ...

    async def list_high_risk(
        self, *, threshold: float = 0.5, hospital_id: UUID | None = None
    ) -> list[ExpiryRiskRecord]:
        """Latest evaluation per batch (not full history) at or above `threshold`."""
        ...

    async def create(self, record: ExpiryRiskRecord) -> ExpiryRiskRecord: ...
