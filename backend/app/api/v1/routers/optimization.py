"""Optimization endpoints. Network-wide (spans multiple hospitals by
design), so `require_own_hospital_or_admin` doesn't cleanly apply here —
restricted to `admin` rather than guessing which hospital "owns" a
cross-network reallocation run.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.v1.deps import CurrentUser, require_role
from app.api.v1.schemas.transfers import TransferRead
from app.application.optimization.service import OptimizationService
from app.core.di import get_optimization_service

router = APIRouter(prefix="/optimization", tags=["Optimization"])

OptimizationServiceDep = Annotated[OptimizationService, Depends(get_optimization_service)]


@router.post(
    "/transfers/{medicine_id}",
    response_model=list[TransferRead],
    dependencies=[Depends(require_role("admin"))],
)
async def optimize_network_transfers(
    medicine_id: UUID, service: OptimizationServiceDep, _current_user: CurrentUser
) -> list[TransferRead]:
    transfers = await service.optimize_network(medicine_id)
    return [TransferRead.model_validate(transfer) for transfer in transfers]
