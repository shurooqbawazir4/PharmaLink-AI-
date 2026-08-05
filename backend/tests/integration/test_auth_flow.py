"""Integration test: register -> login -> access a protected route -> RBAC deny.

Exercises the full stack (router -> service -> repository -> SQLite DB)
through the real FastAPI app, not mocks.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_register_then_login_returns_tokens(client: AsyncClient) -> None:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@medcycle.ai",
            "password": "supersecret123",
            "full_name": "Alice Ahmed",
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["role_name"] == "viewer"

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": "alice@medcycle.ai", "password": "supersecret123"}
    )
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_login_with_wrong_password_is_rejected(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@medcycle.ai", "password": "supersecret123", "full_name": "Bob Bakr"},
    )

    response = await client.post(
        "/api/v1/auth/login", json={"email": "bob@medcycle.ai", "password": "wrong-password"}
    )

    assert response.status_code == 401


async def test_protected_route_requires_bearer_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/hospitals/")
    assert response.status_code in (401, 403)


async def test_me_returns_the_authenticated_user(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "carol@medcycle.ai",
            "password": "supersecret123",
            "full_name": "Carol Cheng",
        },
    )
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": "carol@medcycle.ai", "password": "supersecret123"}
    )
    access_token = login_response.json()["access_token"]

    me_response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "carol@medcycle.ai"


async def test_viewer_cannot_create_hospital(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "dave@medcycle.ai", "password": "supersecret123", "full_name": "Dave Doe"},
    )
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": "dave@medcycle.ai", "password": "supersecret123"}
    )
    access_token = login_response.json()["access_token"]

    response = await client.post(
        "/api/v1/hospitals/",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "name": "Test Hospital",
            "code": "TH-01",
            "latitude": 24.7,
            "longitude": 46.7,
            "city": "Riyadh",
            "region": "Central",
            "bed_capacity": 100,
            "type": "general",
        },
    )

    assert response.status_code == 403
