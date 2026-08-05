"""Hospitals endpoints — the network-node registry every other module joins against."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.v1.deps import CurrentUser, require_role
from app.api.v1.schemas.hospitals import HospitalCreate, HospitalRead, HospitalUpdateOccupancy
from app.application.hospitals.service import HospitalService
from app.core.di import get_hospital_service

router = APIRouter(prefix="/hospitals", tags=["Hospitals"])

HospitalServiceDep = Annotated[HospitalService, Depends(get_hospital_service)]


@router.post(
    "/",
    response_model=HospitalRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin", "hospital_manager"))],
)
async def create_hospital(payload: HospitalCreate, service: HospitalServiceDep) -> HospitalRead:
    hospital = await service.create(**payload.model_dump())
    return HospitalRead.model_validate(hospital)


@router.get("/", response_model=list[HospitalRead])
async def list_hospitals(
    service: HospitalServiceDep,
    _current_user: CurrentUser,
    region: str | None = Query(default=None),
    include_inactive: bool = Query(default=False),
) -> list[HospitalRead]:
    hospitals = await service.list(region=region, include_inactive=include_inactive)
    return [HospitalRead.model_validate(hospital) for hospital in hospitals]


@router.get("/{hospital_id}", response_model=HospitalRead)
async def get_hospital(
    hospital_id: UUID, service: HospitalServiceDep, _current_user: CurrentUser
) -> HospitalRead:
    hospital = await service.get(hospital_id)
    return HospitalRead.model_validate(hospital)


@router.patch(
    "/{hospital_id}/occupancy",
    response_model=HospitalRead,
    dependencies=[Depends(require_role("admin", "hospital_manager"))],
)
async def update_occupancy(
    hospital_id: UUID, payload: HospitalUpdateOccupancy, service: HospitalServiceDep
) -> HospitalRead:
    hospital = await service.update_occupancy(hospital_id, payload.occupancy_rate)
    return HospitalRead.model_validate(hospital)


@router.delete(
    "/{hospital_id}",
    response_model=HospitalRead,
    dependencies=[Depends(require_role("admin"))],
)
async def deactivate_hospital(hospital_id: UUID, service: HospitalServiceDep) -> HospitalRead:
    hospital = await service.deactivate(hospital_id)
    return HospitalRead.model_validate(hospital)
