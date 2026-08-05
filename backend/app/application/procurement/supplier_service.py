"""Supplier use cases — the catalogue Procurement's purchase orders
reference. Suppliers aren't a separate top-level module in the original
spec's 11 backend modules; they're managed as part of Procurement.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.procurement.entities import Supplier
from app.domain.procurement.exceptions import SupplierNotFoundError
from app.domain.procurement.repository import SupplierRepository


class SupplierService:
    def __init__(self, supplier_repository: SupplierRepository) -> None:
        self._suppliers = supplier_repository

    async def create(
        self,
        *,
        name: str,
        lead_time_days: int = 7,
        reliability_score: float = 1.0,
        contact_email: str | None = None,
    ) -> Supplier:
        if not 0.0 <= reliability_score <= 1.0:
            msg = "reliability_score must be between 0.0 and 1.0"
            raise ValueError(msg)
        if lead_time_days <= 0:
            msg = "lead_time_days must be positive"
            raise ValueError(msg)

        supplier = Supplier(
            id=uuid4(),
            name=name,
            contact_email=contact_email,
            lead_time_days=lead_time_days,
            reliability_score=reliability_score,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        return await self._suppliers.create(supplier)

    async def get(self, supplier_id: UUID) -> Supplier:
        supplier = await self._suppliers.get_by_id(supplier_id)
        if supplier is None:
            raise SupplierNotFoundError(str(supplier_id))
        return supplier

    async def list_suppliers(self, *, include_inactive: bool = False) -> list[Supplier]:
        return await self._suppliers.list_suppliers(is_active=None if include_inactive else True)

    async def deactivate(self, supplier_id: UUID) -> Supplier:
        supplier = await self.get(supplier_id)
        supplier.is_active = False
        return await self._suppliers.update(supplier)
