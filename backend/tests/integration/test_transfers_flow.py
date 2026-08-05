"""Integration test: the full Transfers happy path plus hospital-scoped RBAC,
exercised over real HTTP against the actual FastAPI app (router -> service
-> repository -> DB) — not mocks. This is the flow the whole Milestone B
backend exists to support: propose -> approve -> complete actually moves
inventory between two hospitals.
"""

from __future__ import annotations

from httpx import AsyncClient


async def _register_and_assign(
    client: AsyncClient,
    admin_headers: dict[str, str],
    *,
    email: str,
    role_name: str,
    hospital_id: str,
) -> dict[str, str]:
    """Register a user, promote/assign them via the admin endpoint, log in,
    and return their bearer-auth headers."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "full_name": email},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret123"}
    )
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    )
    user_id = me.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/auth/users/{user_id}",
        headers=admin_headers,
        json={"role_name": role_name, "hospital_id": hospital_id},
    )
    assert patch_response.status_code == 200

    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret123"}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


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


async def test_transfer_happy_path_moves_stock_and_enforces_hospital_scope(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    hospital_a_id = await _create_hospital(
        client, admin_headers, code="XFER-A", lat=24.7136, lon=46.6753
    )
    hospital_b_id = await _create_hospital(
        client, admin_headers, code="XFER-B", lat=21.4858, lon=39.1925
    )

    medicine_response = await client.post(
        "/api/v1/medicines/",
        headers=admin_headers,
        json={
            "name": "Insulin",
            "generic_name": "Insulin human",
            "category": "Endocrine",
            "unit": "vial",
            "unit_cost": 5.0,
        },
    )
    assert medicine_response.status_code == 201
    medicine_id = medicine_response.json()["id"]

    pharmacist_a = await _register_and_assign(
        client,
        admin_headers,
        email="pharm-a@medcycle.ai",
        role_name="pharmacist",
        hospital_id=hospital_a_id,
    )
    pharmacist_b = await _register_and_assign(
        client,
        admin_headers,
        email="pharm-b@medcycle.ai",
        role_name="pharmacist",
        hospital_id=hospital_b_id,
    )

    receive_response = await client.post(
        "/api/v1/inventory/receive",
        headers=pharmacist_a,
        json={
            "hospital_id": hospital_a_id,
            "medicine_id": medicine_id,
            "batch_number": "B-XFER-1",
            "quantity": 100,
            "expiry_date": "2027-01-01",
            "unit_cost_at_receipt": 5.0,
            "safety_stock": 10,
        },
    )
    assert receive_response.status_code == 200

    # --- Hospital-scoped RBAC: pharmacist B cannot propose FROM hospital A ---
    forbidden_response = await client.post(
        "/api/v1/transfers/propose",
        headers=pharmacist_b,
        json={
            "source_hospital_id": hospital_a_id,
            "destination_hospital_id": hospital_b_id,
            "medicine_id": medicine_id,
            "quantity": 20,
        },
    )
    assert forbidden_response.status_code == 403

    # --- Happy path: pharmacist A proposes, approves, completes ---
    propose_response = await client.post(
        "/api/v1/transfers/propose",
        headers=pharmacist_a,
        json={
            "source_hospital_id": hospital_a_id,
            "destination_hospital_id": hospital_b_id,
            "medicine_id": medicine_id,
            "quantity": 30,
        },
    )
    assert propose_response.status_code == 200
    transfer = propose_response.json()
    assert transfer["status"] == "proposed"
    assert transfer["distance_km"] > 0

    approve_response = await client.patch(
        f"/api/v1/transfers/{transfer['id']}/approve", headers=pharmacist_a
    )
    assert approve_response.json()["status"] == "approved"

    complete_response = await client.patch(
        f"/api/v1/transfers/{transfer['id']}/complete", headers=pharmacist_a
    )
    completed = complete_response.json()
    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None

    # --- Stock actually moved ---
    hospital_a_inventory = (
        await client.get(f"/api/v1/inventory/?hospital_id={hospital_a_id}", headers=pharmacist_a)
    ).json()
    assert sum(batch["current_stock"] for batch in hospital_a_inventory) == 70

    hospital_b_inventory = (
        await client.get(f"/api/v1/inventory/?hospital_id={hospital_b_id}", headers=pharmacist_a)
    ).json()
    assert sum(batch["current_stock"] for batch in hospital_b_inventory) == 30
