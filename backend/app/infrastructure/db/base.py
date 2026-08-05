"""Declarative base and reusable column mixins for every ORM model.

`Base.metadata` is what Alembic's `env.py` points `target_metadata` at, so
every model module must import from here (never create a second base).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPKMixin:
    """Standard UUID primary key for regular (non-hypertable) tables.

    Uses SQLAlchemy's dialect-agnostic `Uuid` type (native `uuid` on
    Postgres, `CHAR(32)` elsewhere) rather than `postgresql.UUID` directly,
    so the same models can run against SQLite in tests without a second
    set of test-only model definitions.
    """

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """`created_at` / `updated_at`, set/maintained by the database."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
