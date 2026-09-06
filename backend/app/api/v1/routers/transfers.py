"""Transfers endpoints — propose/approve/complete/cancel move physical stock
between hospitals; reads are open to any authenticated user.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import CurrentUser, require_own_hospital_or_admin, require_role
from app.api.v1.schemas.transfers import TransferProposeRequest, TransferRead
from app.application.transfers.service import TransferService
from app.core.di import get_transfer_service
from app.core.exceptions import ForbiddenError
from app.domain.auth.entities import User
from app.domain.shared.enums import TransferStatus
from app.domain.transfers.entities import Transfer

router = APIRouter(prefix="/transfers", tags=["Transfers"])

TransferServiceDep = Annotated[TransferService, Depends(get_transfer_service)]
_TRANSFER_MANAGER_ROLES = ("admin", "hospital_manager", "pharmacist")


def _require_source_or_destination(user: User, transfer: Transfer) -> None:
    """Cancel is the one action either side of a transfer may take — approve
    and complete are source-hospital actions (they're the one releasing
    stock), gated by `require_own_hospital_or_admin` on `source_hospital_id`."""
    if user.has_full_access:
        return
    if user.hospital_id not in (transfer.source_hospital_id, transfer.destination_hospital_id):
        raise ForbiddenError(
            "User is not a member of either hospital on this transfer and cannot cancel it."
        )


@router.post(
    "/propose",
    response_model=TransferRead,
    dependencies=[Depends(require_role(*_TRANSFER_MANAGER_ROLES))],
)
async def propose_transfer(
    payload: TransferProposeRequest, service: TransferServiceDep, current_user: CurrentUser
) -> TransferRead:
    require_own_hospital_or_admin(current_user, payload.source_hospital_id)
    transfer = await service.propose(
        source_hospital_id=payload.source_hospital_id,
        destination_hospital_id=payload.destination_hospital_id,
        medicine_id=payload.medicine_id,
        quantity=payload.quantity,
        created_by=current_user.id,
    )
    return TransferRead.model_validate(transfer)


@router.get("/", response_model=list[TransferRead])
async def list_transfers(
    service: TransferServiceDep,
    _current_user: CurrentUser,
    hospital_id: UUID | None = Query(default=None),
    status: TransferStatus | None = Query(default=None),
    medicine_id: UUID | None = Query(default=None),
) -> list[TransferRead]:
    transfers = await service.list_transfers(
        hospital_id=hospital_id, status=status, medicine_id=medicine_id
    )
    return [TransferRead.model_validate(transfer) for transfer in transfers]


@router.get("/{transfer_id}", response_model=TransferRead)
async def get_transfer(
    transfer_id: UUID, service: TransferServiceDep, _current_user: CurrentUser
) -> TransferRead:
    transfer = await service.get(transfer_id)
    return TransferRead.model_validate(transfer)


@router.patch(
    "/{transfer_id}/approve",
    response_model=TransferRead,
    dependencies=[Depends(require_role(*_TRANSFER_MANAGER_ROLES))],
)
async def approve_transfer(
    transfer_id: UUID, service: TransferServiceDep, current_user: CurrentUser
) -> TransferRead:
    transfer = await service.get(transfer_id)
    require_own_hospital_or_admin(current_user, transfer.source_hospital_id)
    approved = await service.approve(transfer_id)
    return TransferRead.model_validate(approved)


@router.patch(
    "/{transfer_id}/complete",
    response_model=TransferRead,
    dependencies=[Depends(require_role(*_TRANSFER_MANAGER_ROLES))],
)
async def complete_transfer(
    transfer_id: UUID, service: TransferServiceDep, current_user: CurrentUser
) -> TransferRead:
    transfer = await service.get(transfer_id)
    require_own_hospital_or_admin(current_user, transfer.source_hospital_id)
    completed = await service.complete(transfer_id)
    return TransferRead.model_validate(completed)


@router.patch(
    "/{transfer_id}/cancel",
    response_model=TransferRead,
    dependencies=[Depends(require_role(*_TRANSFER_MANAGER_ROLES))],
)
async def cancel_transfer(
    transfer_id: UUID, service: TransferServiceDep, current_user: CurrentUser
) -> TransferRead:
    transfer = await service.get(transfer_id)
    _require_source_or_destination(current_user, transfer)
    cancelled = await service.cancel(transfer_id)
    return TransferRead.model_validate(cancelled)
