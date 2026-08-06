"""Unit tests for ForecastService — no DB, no Docker, no real LightGBM
training (a `FakeForecaster` is injected into a real `MLForecastClient`,
so the client's train-once caching behavior is still exercised for real).
"""

from __future__ import annotations

import uuid

import pytest

from app.application.forecast.service import ForecastService
from app.infrastructure.external.ml_client import MLForecastClient
from tests.unit.fakes import FakeForecaster, FakeForecastRepository


@pytest.fixture
def forecast_repo() -> FakeForecastRepository:
    return FakeForecastRepository()


@pytest.fixture
def fake_forecaster() -> FakeForecaster:
    return FakeForecaster(daily_rate=10.0)


@pytest.fixture
def ml_client(fake_forecaster: FakeForecaster) -> MLForecastClient:
    return MLForecastClient(forecaster=fake_forecaster)


@pytest.fixture
def service(forecast_repo: FakeForecastRepository, ml_client: MLForecastClient) -> ForecastService:
    return ForecastService(forecast_repo, ml_client)


async def test_generate_persists_a_forecast_scaled_by_horizon(service: ForecastService) -> None:
    hospital_id, medicine_id = uuid.uuid4(), uuid.uuid4()

    forecast = await service.generate(hospital_id, medicine_id, horizon_days=30)

    assert forecast.hospital_id == hospital_id
    assert forecast.medicine_id == medicine_id
    assert forecast.predicted_demand == 300.0  # 10/day * 30
    assert forecast.confidence_low < forecast.predicted_demand < forecast.confidence_high


async def test_generate_only_trains_the_model_once(
    service: ForecastService, fake_forecaster: FakeForecaster
) -> None:
    hospital_a, medicine_a = uuid.uuid4(), uuid.uuid4()
    hospital_b, medicine_b = uuid.uuid4(), uuid.uuid4()

    await service.generate(hospital_a, medicine_a)
    await service.generate(hospital_b, medicine_b)

    assert fake_forecaster.fit_call_count == 1


async def test_get_daily_rate_returns_none_when_nothing_generated_yet(
    service: ForecastService,
) -> None:
    rate = await service.get_daily_rate(uuid.uuid4(), uuid.uuid4())
    assert rate is None


async def test_get_daily_rate_normalizes_predicted_demand_by_horizon(
    service: ForecastService,
) -> None:
    hospital_id, medicine_id = uuid.uuid4(), uuid.uuid4()
    await service.generate(hospital_id, medicine_id, horizon_days=30)

    rate = await service.get_daily_rate(hospital_id, medicine_id)

    assert rate == pytest.approx(10.0)
