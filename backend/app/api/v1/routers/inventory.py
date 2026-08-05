"""Inventory endpoints. Reads are open to any authenticated user; mutations
require a stock-managing role AND membership in the target hospital (see
`require_own_hospital_or_admin` in `api/v1/deps.py`).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import CurrentUser, require_own_hospital_or_admin, require_role
from app.api.v1.schemas.inventory import (
    InventoryAdjustRequest,
    InventoryChangeRead,
    InventoryConsumeRequest,
    InventoryRead,
    InventoryReceiveRequest,
)
from app.application.inventory.service import InventoryService
from app.core.di import get_inventory_service

router = APIRouter(prefix="/inventory", tags=["Inventory"])

InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
_STOCK_MANAGER_ROLES = ("admin", "hospital_manager", "pharmacist")


@router.get("/", response_model=list[InventoryRead])
async def list_inventory(
    service: InventoryServiceDep,
    _current_user: CurrentUser,
    hospital_id: UUID | None = Query(default=None),
    medicine_id: UUID | None = Query(default=None),
) -> list[InventoryRead]:
    batches = await service.list_batches(hospital_id=hospital_id, medicine_id=medicine_id)
    return [InventoryRead.model_validate(batch) for batch in batches]


@router.get("/expiring-soon", response_model=list[InventoryRead])
async def list_expiring_soon(
    service: InventoryServiceDep,
    _current_user: CurrentUser,
    hospital_id: UUID | None = Query(default=None),
    within_days: int = Query(default=30, gt=0),
) -> list[InventoryRead]:
    batches = await service.list_expiring_soon(hospital_id=hospital_id, within_days=within_days)
    return [InventoryRead.model_validate(batch) for batch in batches]


@router.get("/below-safety-stock", response_model=list[InventoryRead])
async def list_below_safety_stock(
    service: InventoryServiceDep,
    _current_user: CurrentUser,
    hospital_id: UUID | None = Query(default=None),
) -> list[InventoryRead]:
    batches = await service.list_below_safety_stock(hospital_id=hospital_id)
    return [InventoryRead.model_validate(batch) for batch in batches]


@router.get("/{inventory_id}", response_model=InventoryRead)
async def get_inventory_batch(
    inventory_id: UUID, service: InventoryServiceDep, _current_user: CurrentUser
) -> InventoryRead:
    batch = await service.get(inventory_id)
    return InventoryRead.model_validate(batch)


@router.post(
    "/receive",
    response_model=InventoryRead,
    dependencies=[Depends(require_role(*_STOCK_MANAGER_ROLES))],
)
async def receive_stock(
    payload: InventoryReceiveRequest, service: InventoryServiceDep, current_user: CurrentUser
) -> InventoryRead:
    require_own_hospital_or_admin(current_user, payload.hospital_id)
    batch = await service.receive_stock(**payload.model_dump())
    return InventoryRead.model_validate(batch)


@router.post(
    "/{inventory_id}/consume",
    response_model=InventoryChangeRead,
    dependencies=[Depends(require_role(*_STOCK_MANAGER_ROLES))],
)
async def consume_stock(
    inventory_id: UUID,
    payload: InventoryConsumeRequest,
    service: InventoryServiceDep,
    current_user: CurrentUser,
) -> InventoryChangeRead:
    batch = await service.get(inventory_id)
    require_own_hospital_or_admin(current_user, batch.hospital_id)
    change = await service.consume(inventory_id, payload.quantity)
    return InventoryChangeRead(
        batch=InventoryRead.model_validate(change.batch),
        change_qty=change.change_qty,
        reason=change.reason,
        recorded_at=change.recorded_at,
    )


@router.post(
    "/{inventory_id}/write-off",
    response_model=InventoryChangeRead,
    dependencies=[Depends(require_role(*_STOCK_MANAGER_ROLES))],
)
async def write_off_expired(
    inventory_id: UUID, service: InventoryServiceDep, current_user: CurrentUser
) -> InventoryChangeRead:
    batch = await service.get(inventory_id)
    require_own_hospital_or_admin(current_user, batch.hospital_id)
    change = await service.write_off_expired(inventory_id)
    return InventoryChangeRead(
        batch=InventoryRead.model_validate(change.batch),
        change_qty=change.change_qty,
        reason=change.reason,
        recorded_at=change.recorded_at,
    )


@router.post(
    "/{inventory_id}/adjust",
    response_model=InventoryChangeRead,
    dependencies=[Depends(require_role(*_STOCK_MANAGER_ROLES))],
)
async def adjust_stock(
    inventory_id: UUID,
    payload: InventoryAdjustRequest,
    service: InventoryServiceDep,
    current_user: CurrentUser,
) -> InventoryChangeRead:
    batch = await service.get(inventory_id)
    require_own_hospital_or_admin(current_user, batch.hospital_id)
    change = await service.adjust(inventory_id, payload.change_qty)
    return InventoryChangeRead(
        batch=InventoryRead.model_validate(change.batch),
        change_qty=change.change_qty,
        reason=change.reason,
        recorded_at=change.recorded_at,
    )
