"""SQLAlchemy implementation of `app.domain.forecast.repository.ForecastRepository`.

`get_training_data`/`get_recent_history` join `consumption` (grouped to
one row per hospital+medicine+day) against `weather` by the consuming
hospital's actual region and that day's date — the real per-day
flu-activity signal a forecast should train against, not a shortcut.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.forecast.entities import Forecast
from app.domain.forecast.repository import ConsumptionRow
from app.infrastructure.db.models import (
    ConsumptionModel,
    ForecastModel,
    HospitalModel,
    WeatherModel,
)


class SQLAlchemyForecastRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_latest(self, hospital_id: UUID, medicine_id: UUID) -> Forecast | None:
        stmt = (
            select(ForecastModel)
            .where(
                ForecastModel.hospital_id == hospital_id, ForecastModel.medicine_id == medicine_id
            )
            .order_by(ForecastModel.generated_at.desc())
            .limit(1)
        )
        model = await self._db.scalar(stmt)
        return self._to_entity(model) if model else None

    async def list_forecasts(
        self,
        *,
        hospital_id: UUID | None = None,
        medicine_id: UUID | None = None,
    ) -> list[Forecast]:
        stmt = select(ForecastModel)
        if hospital_id is not None:
            stmt = stmt.where(ForecastModel.hospital_id == hospital_id)
        if medicine_id is not None:
            stmt = stmt.where(ForecastModel.medicine_id == medicine_id)
        stmt = stmt.order_by(ForecastModel.generated_at.desc())
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    async def create(self, forecast: Forecast) -> Forecast:
        model = ForecastModel(
            id=forecast.id,
            generated_at=forecast.generated_at,
            hospital_id=forecast.hospital_id,
            medicine_id=forecast.medicine_id,
            horizon_days=forecast.horizon_days,
            model_used=forecast.model_used,
            predicted_demand=forecast.predicted_demand,
            confidence_low=forecast.confidence_low,
            confidence_high=forecast.confidence_high,
        )
        self._db.add(model)
        await self._db.flush()
        return self._to_entity(model)

    async def get_training_data(self) -> list[ConsumptionRow]:
        return await self._consumption_query()

    async def get_recent_history(
        self, hospital_id: UUID, medicine_id: UUID, *, since: date
    ) -> list[ConsumptionRow]:
        return await self._consumption_query(
            hospital_id=hospital_id, medicine_id=medicine_id, since=since
        )

    async def _consumption_query(
        self,
        *,
        hospital_id: UUID | None = None,
        medicine_id: UUID | None = None,
        since: date | None = None,
    ) -> list[ConsumptionRow]:
        consumed_date = func.date(ConsumptionModel.consumed_at)
        stmt = (
            select(
                ConsumptionModel.hospital_id,
                ConsumptionModel.medicine_id,
                consumed_date.label("date"),
                func.sum(ConsumptionModel.quantity).label("quantity"),
                func.max(WeatherModel.flu_activity_index).label("flu_activity_index"),
            )
            .join(HospitalModel, HospitalModel.id == ConsumptionModel.hospital_id)
            .outerjoin(
                WeatherModel,
                and_(
                    WeatherModel.region == HospitalModel.region,
                    WeatherModel.recorded_date == consumed_date,
                ),
            )
            .group_by(ConsumptionModel.hospital_id, ConsumptionModel.medicine_id, consumed_date)
            .order_by(consumed_date)
        )
        if hospital_id is not None:
            stmt = stmt.where(ConsumptionModel.hospital_id == hospital_id)
        if medicine_id is not None:
            stmt = stmt.where(ConsumptionModel.medicine_id == medicine_id)
        if since is not None:
            stmt = stmt.where(consumed_date >= since)

        rows = await self._db.execute(stmt)
        return [
            ConsumptionRow(
                hospital_id=str(row.hospital_id),
                medicine_id=str(row.medicine_id),
                date=row.date,
                quantity=int(row.quantity),
                flu_activity_index=(
                    float(row.flu_activity_index) if row.flu_activity_index is not None else None
                ),
            )
            for row in rows
        ]

    @staticmethod
    def _to_entity(model: ForecastModel) -> Forecast:
        return Forecast(
            id=model.id,
            hospital_id=model.hospital_id,
            medicine_id=model.medicine_id,
            horizon_days=model.horizon_days,
            model_used=model.model_used,
            predicted_demand=model.predicted_demand,
            confidence_low=model.confidence_low,
            confidence_high=model.confidence_high,
            generated_at=model.generated_at,
        )
