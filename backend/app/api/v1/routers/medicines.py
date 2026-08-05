"""Medicines endpoints — the catalogue every inventory/forecast/order references."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import CurrentUser, require_role
from app.api.v1.schemas.medicines import MedicineCreate, MedicineRead, MedicineUpdateCost
from app.application.medicines.service import MedicineService
from app.core.di import get_medicine_service

router = APIRouter(prefix="/medicines", tags=["Medicines"])

MedicineServiceDep = Annotated[MedicineService, Depends(get_medicine_service)]


@router.post(
    "/",
    response_model=MedicineRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin", "pharmacist"))],
)
async def create_medicine(payload: MedicineCreate, service: MedicineServiceDep) -> MedicineRead:
    medicine = await service.create(**payload.model_dump())
    return MedicineRead.model_validate(medicine)


@router.get("/", response_model=list[MedicineRead])
async def list_medicines(
    service: MedicineServiceDep,
    _current_user: CurrentUser,
    category: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
) -> list[MedicineRead]:
    medicines = await service.list(category=category, include_inactive=include_inactive)
    return [MedicineRead.model_validate(medicine) for medicine in medicines]


@router.get("/{medicine_id}", response_model=MedicineRead)
async def get_medicine(
    medicine_id: UUID, service: MedicineServiceDep, _current_user: CurrentUser
) -> MedicineRead:
    medicine = await service.get(medicine_id)
    return MedicineRead.model_validate(medicine)


@router.patch(
    "/{medicine_id}/unit-cost",
    response_model=MedicineRead,
    dependencies=[Depends(require_role("admin", "pharmacist"))],
)
async def update_unit_cost(
    medicine_id: UUID, payload: MedicineUpdateCost, service: MedicineServiceDep
) -> MedicineRead:
    medicine = await service.update_unit_cost(medicine_id, payload.unit_cost)
    return MedicineRead.model_validate(medicine)


@router.delete(
    "/{medicine_id}",
    response_model=MedicineRead,
    dependencies=[Depends(require_role("admin"))],
)
async def deactivate_medicine(medicine_id: UUID, service: MedicineServiceDep) -> MedicineRead:
    medicine = await service.deactivate(medicine_id)
    return MedicineRead.model_validate(medicine)
