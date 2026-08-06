"""Integration tests for the Milestone C surface: Forecast, Optimization,
and Assistant endpoints — exercised over real HTTP against the real
FastAPI app (router -> service -> repository -> DB). Only the actual
model computation is faked (`FakeForecaster`/`FakeLLMProvider`, via
`app.dependency_overrides`), so these tests don't depend on real LightGBM
training-data volume or a live Groq call — everything else is real.
"""

from __future__ import annotations

from httpx import AsyncClient

from app.core.di import get_llm_provider, get_ml_forecast_client
from app.infrastructure.external.ml_client import MLForecastClient
from app.main import app
from tests.unit.fakes import FakeForecaster, FakeLLMProvider


async def _create_hospital(
    client: AsyncClient, admin_headers: dict[str, str], *, code: str, lat: float, lon: float
) -> str:
    response = await client.post(
        "/api/v1/hospitals/",
        headers=admin_headers,
        json={
            "name": f"Hospital {code}",
            "code": code,
            "latitude": lat,
            "longitude": lon,
            "city": "City",
            "region": "Region",
            "bed_capacity": 200,
            "type": "general",
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


async def _create_medicine(client: AsyncClient, admin_headers: dict[str, str], *, name: str) -> str:
    response = await client.post(
        "/api/v1/medicines/",
        headers=admin_headers,
        json={
            "name": name,
            "generic_name": name,
            "category": "General",
            "unit": "unit",
            "unit_cost": 5.0,
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


async def _receive_stock(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    hospital_id: str,
    medicine_id: str,
    quantity: int,
    safety_stock: int,
) -> None:
    response = await client.post(
        "/api/v1/inventory/receive",
        headers=headers,
        json={
            "hospital_id": hospital_id,
            "medicine_id": medicine_id,
            "batch_number": "B1",
            "quantity": quantity,
            "expiry_date": "2027-01-01",
            "unit_cost_at_receipt": 5.0,
            "safety_stock": safety_stock,
        },
    )
    assert response.status_code == 200


async def test_generate_and_fetch_forecast(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    app.dependency_overrides[get_ml_forecast_client] = lambda: MLForecastClient(
        forecaster=FakeForecaster(daily_rate=8.0)
    )
    try:
        hospital_id = await _create_hospital(client, admin_headers, code="FC-A", lat=24.7, lon=46.7)
        medicine_id = await _create_medicine(client, admin_headers, name="Amoxicillin")

        generate_response = await client.post(
            f"/api/v1/forecasts/generate/{hospital_id}/{medicine_id}?horizon_days=14",
            headers=admin_headers,
        )
        assert generate_response.status_code == 200
        forecast = generate_response.json()
        assert forecast["predicted_demand"] == 112.0  # 8/day * 14
        assert forecast["model_used"] == "lightgbm"

        latest_response = await client.get(
            f"/api/v1/forecasts/latest/{hospital_id}/{medicine_id}", headers=admin_headers
        )
        assert latest_response.status_code == 200
        assert latest_response.json()["id"] == forecast["id"]
    finally:
        app.dependency_overrides.pop(get_ml_forecast_client, None)


async def test_forecast_not_found_returns_404(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    hospital_id = await _create_hospital(client, admin_headers, code="FC-NONE", lat=24.7, lon=46.7)
    medicine_id = await _create_medicine(client, admin_headers, name="Ibuprofen")

    response = await client.get(
        f"/api/v1/forecasts/latest/{hospital_id}/{medicine_id}", headers=admin_headers
    )

    assert response.status_code == 404


async def test_optimize_network_transfers_creates_ai_recommended_transfer(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    surplus_id = await _create_hospital(
        client, admin_headers, code="OPT-A", lat=24.7136, lon=46.6753
    )
    deficit_id = await _create_hospital(
        client, admin_headers, code="OPT-B", lat=21.4858, lon=39.1925
    )
    medicine_id = await _create_medicine(client, admin_headers, name="Salbutamol")

    await _receive_stock(
        client,
        admin_headers,
        hospital_id=surplus_id,
        medicine_id=medicine_id,
        quantity=200,
        safety_stock=20,
    )
    await _receive_stock(
        client,
        admin_headers,
        hospital_id=deficit_id,
        medicine_id=medicine_id,
        quantity=10,
        safety_stock=20,
    )

    response = await client.post(
        f"/api/v1/optimization/transfers/{medicine_id}", headers=admin_headers
    )

    assert response.status_code == 200
    transfers = response.json()
    assert len(transfers) == 1
    assert transfers[0]["source_hospital_id"] == surplus_id
    assert transfers[0]["destination_hospital_id"] == deficit_id
    assert transfers[0]["recommended_by"] == "ai"


async def test_explain_transfer_and_chat_use_the_fake_llm(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    fake_llm = FakeLLMProvider(response="Moving stock prevents a shortage.")
    app.dependency_overrides[get_llm_provider] = lambda: fake_llm
    try:
        source_id = await _create_hospital(client, admin_headers, code="LLM-A", lat=24.7, lon=46.7)
        dest_id = await _create_hospital(client, admin_headers, code="LLM-B", lat=21.5, lon=39.2)
        medicine_id = await _create_medicine(client, admin_headers, name="Paracetamol")
        await _receive_stock(
            client,
            admin_headers,
            hospital_id=source_id,
            medicine_id=medicine_id,
            quantity=100,
            safety_stock=5,
        )

        propose_response = await client.post(
            "/api/v1/transfers/propose",
            headers=admin_headers,
            json={
                "source_hospital_id": source_id,
                "destination_hospital_id": dest_id,
                "medicine_id": medicine_id,
                "quantity": 20,
            },
        )
        assert propose_response.status_code == 200
        transfer_id = propose_response.json()["id"]

        explain_response = await client.get(
            f"/api/v1/assistant/explain/transfer/{transfer_id}", headers=admin_headers
        )
        assert explain_response.status_code == 200
        assert explain_response.json()["explanation"] == "Moving stock prevents a shortage."
        assert fake_llm.last_system_prompt is not None
        # Prompt grounds the explanation with the medicine's real NAME, not a raw UUID.
        assert "Paracetamol" in fake_llm.last_messages[0].content

        chat_response = await client.post(
            "/api/v1/assistant/chat",
            headers=admin_headers,
            json={"question": "What is my highest risk medicine?"},
        )
        assert chat_response.status_code == 200
        assert chat_response.json()["answer"] == "Moving stock prevents a shortage."
    finally:
        app.dependency_overrides.pop(get_llm_provider, None)
