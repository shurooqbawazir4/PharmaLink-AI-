"""Procurement endpoints: suppliers (a network-wide catalogue, like
Hospitals/Medicines) and purchase orders (hospital-scoped, like Inventory).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import CurrentUser, require_own_hospital_or_admin, require_role
from app.api.v1.schemas.procurement import (
    PurchaseOrderRead,
    PurchaseOrderReceiveRequest,
    SupplierCreate,
    SupplierRead,
)
from app.application.procurement.service import ProcurementService
from app.application.procurement.supplier_service import SupplierService
from app.core.di import get_procurement_service, get_supplier_service
from app.domain.shared.enums import PurchaseOrderStatus

suppliers_router = APIRouter(prefix="/suppliers", tags=["Procurement"])
purchase_orders_router = APIRouter(prefix="/purchase-orders", tags=["Procurement"])

SupplierServiceDep = Annotated[SupplierService, Depends(get_supplier_service)]
ProcurementServiceDep = Annotated[ProcurementService, Depends(get_procurement_service)]
_PROCUREMENT_MANAGER_ROLES = ("admin", "hospital_manager", "pharmacist")


# --- Suppliers (network-wide catalogue) -------------------------------------


@suppliers_router.post(
    "/",
    response_model=SupplierRead,
    status_code=201,
    dependencies=[Depends(require_role(*_PROCUREMENT_MANAGER_ROLES))],
)
async def create_supplier(payload: SupplierCreate, service: SupplierServiceDep) -> SupplierRead:
    supplier = await service.create(**payload.model_dump())
    return SupplierRead.model_validate(supplier)


@suppliers_router.get("/", response_model=list[SupplierRead])
async def list_suppliers(
    service: SupplierServiceDep,
    _current_user: CurrentUser,
    include_inactive: bool = Query(default=False),
) -> list[SupplierRead]:
    suppliers = await service.list_suppliers(include_inactive=include_inactive)
    return [SupplierRead.model_validate(supplier) for supplier in suppliers]


@suppliers_router.get("/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: UUID, service: SupplierServiceDep, _current_user: CurrentUser
) -> SupplierRead:
    supplier = await service.get(supplier_id)
    return SupplierRead.model_validate(supplier)


@suppliers_router.delete(
    "/{supplier_id}",
    response_model=SupplierRead,
    dependencies=[Depends(require_role("admin"))],
)
async def deactivate_supplier(supplier_id: UUID, service: SupplierServiceDep) -> SupplierRead:
    supplier = await service.deactivate(supplier_id)
    return SupplierRead.model_validate(supplier)


# --- Purchase orders (hospital-scoped) --------------------------------------


@purchase_orders_router.post(
    "/recommend/{hospital_id}",
    response_model=list[PurchaseOrderRead],
    dependencies=[Depends(require_role(*_PROCUREMENT_MANAGER_ROLES))],
)
async def recommend_purchase_orders(
    hospital_id: UUID, service: ProcurementServiceDep, current_user: CurrentUser
) -> list[PurchaseOrderRead]:
    require_own_hospital_or_admin(current_user, hospital_id)
    orders = await service.recommend_for_hospital(hospital_id)
    return [PurchaseOrderRead.model_validate(order) for order in orders]


@purchase_orders_router.get("/", response_model=list[PurchaseOrderRead])
async def list_purchase_orders(
    service: ProcurementServiceDep,
    _current_user: CurrentUser,
    hospital_id: UUID | None = Query(default=None),
    status: PurchaseOrderStatus | None = Query(default=None),
    medicine_id: UUID | None = Query(default=None),
) -> list[PurchaseOrderRead]:
    orders = await service.list_orders(
        hospital_id=hospital_id, status=status, medicine_id=medicine_id
    )
    return [PurchaseOrderRead.model_validate(order) for order in orders]


@purchase_orders_router.get("/{order_id}", response_model=PurchaseOrderRead)
async def get_purchase_order(
    order_id: UUID, service: ProcurementServiceDep, _current_user: CurrentUser
) -> PurchaseOrderRead:
    order = await service.get(order_id)
    return PurchaseOrderRead.model_validate(order)


@purchase_orders_router.patch(
    "/{order_id}/approve",
    response_model=PurchaseOrderRead,
    dependencies=[Depends(require_role(*_PROCUREMENT_MANAGER_ROLES))],
)
async def approve_purchase_order(
    order_id: UUID, service: ProcurementServiceDep, current_user: CurrentUser
) -> PurchaseOrderRead:
    order = await service.get(order_id)
    require_own_hospital_or_admin(current_user, order.hospital_id)
    approved = await service.approve(order_id)
    return PurchaseOrderRead.model_validate(approved)


@purchase_orders_router.patch(
    "/{order_id}/mark-ordered",
    response_model=PurchaseOrderRead,
    dependencies=[Depends(require_role(*_PROCUREMENT_MANAGER_ROLES))],
)
async def mark_purchase_order_ordered(
    order_id: UUID, service: ProcurementServiceDep, current_user: CurrentUser
) -> PurchaseOrderRead:
    order = await service.get(order_id)
    require_own_hospital_or_admin(current_user, order.hospital_id)
    updated = await service.mark_ordered(order_id)
    return PurchaseOrderRead.model_validate(updated)


@purchase_orders_router.patch(
    "/{order_id}/receive",
    response_model=PurchaseOrderRead,
    dependencies=[Depends(require_role(*_PROCUREMENT_MANAGER_ROLES))],
)
async def receive_purchase_order(
    order_id: UUID,
    payload: PurchaseOrderReceiveRequest,
    service: ProcurementServiceDep,
    current_user: CurrentUser,
) -> PurchaseOrderRead:
    order = await service.get(order_id)
    require_own_hospital_or_admin(current_user, order.hospital_id)
    received = await service.mark_received(
        order_id, batch_number=payload.batch_number, expiry_date=payload.expiry_date
    )
    return PurchaseOrderRead.model_validate(received)


@purchase_orders_router.patch(
    "/{order_id}/cancel",
    response_model=PurchaseOrderRead,
    dependencies=[Depends(require_role(*_PROCUREMENT_MANAGER_ROLES))],
)
async def cancel_purchase_order(
    order_id: UUID, service: ProcurementServiceDep, current_user: CurrentUser
) -> PurchaseOrderRead:
    order = await service.get(order_id)
    require_own_hospital_or_admin(current_user, order.hospital_id)
    cancelled = await service.cancel(order_id)
    return PurchaseOrderRead.model_validate(cancelled)
