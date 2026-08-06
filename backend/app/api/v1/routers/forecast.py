"""Forecast endpoints. Generation is triggered manually for now (same
pattern as Expiry's evaluate endpoints); Milestone C also exposes the same
service method as a Celery task (infrastructure/tasks/forecast_tasks.py)
for batch/scheduled refreshes.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.deps import CurrentUser, require_own_hospital_or_admin, require_role
from app.api.v1.schemas.forecast import ForecastRead
from app.application.forecast.service import ForecastService
from app.core.di import get_forecast_service

router = APIRouter(prefix="/forecasts", tags=["Forecast"])

ForecastServiceDep = Annotated[ForecastService, Depends(get_forecast_service)]
_FORECAST_MANAGER_ROLES = ("admin", "hospital_manager", "pharmacist")


@router.post(
    "/generate/{hospital_id}/{medicine_id}",
    response_model=ForecastRead,
    dependencies=[Depends(require_role(*_FORECAST_MANAGER_ROLES))],
)
async def generate_forecast(
    hospital_id: UUID,
    medicine_id: UUID,
    service: ForecastServiceDep,
    current_user: CurrentUser,
    horizon_days: int = Query(default=30, gt=0, le=365),
) -> ForecastRead:
    require_own_hospital_or_admin(current_user, hospital_id)
    forecast = await service.generate(hospital_id, medicine_id, horizon_days)
    return ForecastRead.model_validate(forecast)


@router.get("/", response_model=list[ForecastRead])
async def list_forecasts(
    service: ForecastServiceDep,
    _current_user: CurrentUser,
    hospital_id: UUID | None = Query(default=None),
    medicine_id: UUID | None = Query(default=None),
) -> list[ForecastRead]:
    forecasts = await service.list_forecasts(hospital_id=hospital_id, medicine_id=medicine_id)
    return [ForecastRead.model_validate(forecast) for forecast in forecasts]


@router.get("/latest/{hospital_id}/{medicine_id}", response_model=ForecastRead)
async def get_latest_forecast(
    hospital_id: UUID, medicine_id: UUID, service: ForecastServiceDep, _current_user: CurrentUser
) -> ForecastRead:
    forecast = await service.get_latest(hospital_id, medicine_id)
    if forecast is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No forecast exists yet for hospital '{hospital_id}' / "
                f"medicine '{medicine_id}'."
            ),
        )
    return ForecastRead.model_validate(forecast)
