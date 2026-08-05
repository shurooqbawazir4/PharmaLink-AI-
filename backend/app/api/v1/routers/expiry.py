"""Expiry-risk endpoints. Evaluation is triggered manually for now (a
button/cron in later milestones); Milestone C adds a Celery job that runs
this on a schedule using the same `ExpiryService.evaluate_hospital`.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.deps import CurrentUser, require_own_hospital_or_admin, require_role
from app.api.v1.schemas.expiry import ExpiryRiskRead
from app.application.expiry.service import ExpiryService
from app.application.inventory.service import InventoryService
from app.core.di import get_expiry_service, get_inventory_service

router = APIRouter(prefix="/expiry", tags=["Expiry"])

ExpiryServiceDep = Annotated[ExpiryService, Depends(get_expiry_service)]
InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
_EXPIRY_MANAGER_ROLES = ("admin", "hospital_manager", "pharmacist")


@router.get("/high-risk", response_model=list[ExpiryRiskRead])
async def list_high_risk(
    service: ExpiryServiceDep,
    _current_user: CurrentUser,
    hospital_id: UUID | None = Query(default=None),
    threshold: float = Query(default=0.5, ge=0.0, le=1.0),
) -> list[ExpiryRiskRead]:
    records = await service.list_high_risk(threshold=threshold, hospital_id=hospital_id)
    return [ExpiryRiskRead.model_validate(record) for record in records]


@router.get("/inventory/{inventory_id}/latest", response_model=ExpiryRiskRead)
async def get_latest_for_inventory(
    inventory_id: UUID, service: ExpiryServiceDep, _current_user: CurrentUser
) -> ExpiryRiskRead:
    record = await service.get_latest_for_inventory(inventory_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No expiry-risk evaluation exists yet for inventory batch '{inventory_id}'.",
        )
    return ExpiryRiskRead.model_validate(record)


@router.post(
    "/evaluate/{inventory_id}",
    response_model=ExpiryRiskRead,
    dependencies=[Depends(require_role(*_EXPIRY_MANAGER_ROLES))],
)
async def evaluate_batch(
    inventory_id: UUID,
    expiry_service: ExpiryServiceDep,
    inventory_service: InventoryServiceDep,
    current_user: CurrentUser,
) -> ExpiryRiskRead:
    batch = await inventory_service.get(inventory_id)
    require_own_hospital_or_admin(current_user, batch.hospital_id)
    record = await expiry_service.evaluate_batch(inventory_id)
    return ExpiryRiskRead.model_validate(record)


@router.post(
    "/evaluate-hospital/{hospital_id}",
    response_model=list[ExpiryRiskRead],
    dependencies=[Depends(require_role(*_EXPIRY_MANAGER_ROLES))],
)
async def evaluate_hospital(
    hospital_id: UUID, service: ExpiryServiceDep, current_user: CurrentUser
) -> list[ExpiryRiskRead]:
    require_own_hospital_or_admin(current_user, hospital_id)
    records = await service.evaluate_hospital(hospital_id)
    return [ExpiryRiskRead.model_validate(record) for record in records]
