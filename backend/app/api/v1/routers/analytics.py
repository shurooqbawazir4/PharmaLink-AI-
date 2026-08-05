"""Analytics endpoints — read-only KPI reporting, open to any authenticated user."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import CurrentUser
from app.api.v1.schemas.analytics import KPISummaryRead
from app.application.analytics.service import AnalyticsService
from app.core.di import get_analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])

AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.get("/kpis", response_model=KPISummaryRead)
async def get_kpi_summary(
    service: AnalyticsServiceDep,
    _current_user: CurrentUser,
    hospital_id: UUID | None = Query(default=None),
) -> KPISummaryRead:
    summary = await service.get_kpi_summary(hospital_id)
    return KPISummaryRead.model_validate(summary)
