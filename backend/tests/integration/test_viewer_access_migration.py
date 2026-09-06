"""Verify the deployment migration grants viewer access without changing other roles."""

import runpy
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select

from app.infrastructure.db.models import RoleModel


async def test_viewer_access_migration(session_factory):
    migration = runpy.run_path(str(
        Path(__file__).resolve().parents[2] / "alembic/versions/0003_viewer_full_access.py"
    ))
    async with session_factory() as session:
        viewer = await session.scalar(select(RoleModel).where(RoleModel.name == "viewer"))
        viewer.permissions = ["medicines:read"]
        await session.commit()
        connection = await session.connection()

        def migrate(sync_connection, direction):
            with Operations.context(MigrationContext.configure(sync_connection)):
                migration[direction]()

        await connection.run_sync(migrate, "upgrade")
        await connection.run_sync(migrate, "upgrade")
        session.expire_all()
        viewer = await session.scalar(select(RoleModel).where(RoleModel.name == "viewer"))
        assert viewer.permissions == ["medicines:read", "*"]
        pharmacist = await session.scalar(select(RoleModel).where(RoleModel.name == "pharmacist"))
        assert pharmacist.permissions == ["medicines:write", "inventory:write"]
        await connection.run_sync(migrate, "downgrade")
        session.expire_all()
        viewer = await session.scalar(select(RoleModel).where(RoleModel.name == "viewer"))
        assert viewer.permissions == ["medicines:read"]
