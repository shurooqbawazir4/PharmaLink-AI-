"""Repository interfaces for the procurement module (suppliers + orders)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.procurement.entities import PurchaseOrder, Supplier
from app.domain.shared.enums import PurchaseOrderStatus


class SupplierRepository(Protocol):
    async def get_by_id(self, supplier_id: UUID) -> Supplier | None: ...

    async def list_suppliers(self, *, is_active: bool | None = True) -> list[Supplier]: ...

    async def create(self, supplier: Supplier) -> Supplier: ...

    async def update(self, supplier: Supplier) -> Supplier: ...


class PurchaseOrderRepository(Protocol):
    async def get_by_id(self, order_id: UUID) -> PurchaseOrder | None: ...

    async def list_orders(
        self,
        *,
        hospital_id: UUID | None = None,
        status: PurchaseOrderStatus | None = None,
        medicine_id: UUID | None = None,
    ) -> list[PurchaseOrder]: ...

    async def create(self, order: PurchaseOrder) -> PurchaseOrder: ...

    async def update(self, order: PurchaseOrder) -> PurchaseOrder: ...
