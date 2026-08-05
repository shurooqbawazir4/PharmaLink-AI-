"""Shared pytest fixtures: an in-memory SQLite DB (schema-compatible with
Postgres thanks to the dialect-agnostic column types in
`infrastructure/db/models.py`) and an `httpx.AsyncClient` wired to the real
FastAPI app via dependency overrides — no Docker required for this suite.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import RoleModel, UserModel
from app.main import app

# Seeded once per test DB — mirrors the roles the initial migration seeds
# in real environments (see docs/database.md).
_SEED_ROLES = [
    ("admin", ["*"]),
    ("hospital_manager", ["hospitals:write", "transfers:write", "procurement:write"]),
    ("pharmacist", ["medicines:write", "inventory:write"]),
    ("viewer", []),
]


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        session.add_all(RoleModel(name=name, permissions=perms) for name, perms in _SEED_ROLES)
        await session.commit()

    yield factory

    await engine.dispose()


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = _override_get_db
    # AuditLogMiddleware lives outside the Depends graph (see
    # app/core/logging.py) and reads its session factory from `app.state`
    # instead — point it at the same in-memory test DB.
    original_audit_factory = app.state.audit_session_factory
    app.state.audit_session_factory = session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    app.state.audit_session_factory = original_audit_factory


@pytest.fixture
async def admin_headers(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> dict[str, str]:
    """Registers a fresh user and promotes it to `admin` directly against
    the DB — the same bootstrap every real deployment needs, since the
    `PATCH /auth/users/{id}` promotion endpoint is itself admin-gated (no
    API path can create the very first admin). `scripts/seed_database.py`
    does the equivalent for real environments."""
    email = "test-admin@medcycle.ai"
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123", "full_name": "Test Admin"},
    )
    # session.get() needs an actual UUID, not the JSON response's str form.
    user_id = UUID(register_response.json()["id"])

    async with session_factory() as session:
        admin_role = await session.scalar(select(RoleModel).where(RoleModel.name == "admin"))
        user = await session.get(UserModel, user_id)
        assert admin_role is not None
        assert user is not None
        user.role_id = admin_role.id
        await session.commit()

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret123"}
    )
    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}
