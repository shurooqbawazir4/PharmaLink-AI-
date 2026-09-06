"""Grant the viewer role full access.

Revision ID: b42f6e81d903
Revises: acaf3ef4a22d
"""
from alembic import op
import sqlalchemy as sa

revision = "b42f6e81d903"
down_revision = "acaf3ef4a22d"
branch_labels = None
depends_on = None


def _set_wildcard(enabled: bool) -> None:
    roles = sa.table(
        "roles", sa.column("name", sa.String()), sa.column("permissions", sa.JSON())
    )
    connection = op.get_bind()
    row = connection.execute(
        sa.select(roles.c.permissions).where(roles.c.name == "viewer")
    ).first()
    if row is None:
        raise RuntimeError("Viewer role is missing; initial role seeding must run first.")
    permissions = list(row[0] or [])
    if enabled and "*" not in permissions:
        permissions.append("*")
    elif not enabled:
        permissions = [permission for permission in permissions if permission != "*"]
    connection.execute(
        roles.update().where(roles.c.name == "viewer").values(permissions=permissions)
    )


def upgrade() -> None:
    _set_wildcard(True)


def downgrade() -> None:
    _set_wildcard(False)
