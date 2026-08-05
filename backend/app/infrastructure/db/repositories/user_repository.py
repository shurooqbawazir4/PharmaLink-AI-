"""SQLAlchemy implementation of `app.domain.auth.repository.UserRepository`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.auth.entities import User
from app.infrastructure.db.models import RoleModel, UserModel


class SQLAlchemyUserRepository:
    """Implements `UserRepository` — see that Protocol for the contract."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        stmt = (
            select(UserModel).options(selectinload(UserModel.role)).where(UserModel.id == user_id)
        )
        model = await self._db.scalar(stmt)
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(UserModel)
            .options(selectinload(UserModel.role))
            .where(UserModel.email == email)
        )
        model = await self._db.scalar(stmt)
        return self._to_entity(model) if model else None

    async def create(self, user: User) -> User:
        role = await self._db.scalar(select(RoleModel).where(RoleModel.name == user.role_name))
        if role is None:
            msg = f"Role '{user.role_name}' does not exist — seed roles before creating users."
            raise ValueError(msg)

        model = UserModel(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            role_id=role.id,
            hospital_id=user.hospital_id,
            is_active=user.is_active,
        )
        self._db.add(model)
        await self._db.flush()
        return self._to_entity(model, role_name=role.name)

    async def update(self, user: User) -> User:
        role = await self._db.scalar(select(RoleModel).where(RoleModel.name == user.role_name))
        if role is None:
            msg = f"Role '{user.role_name}' does not exist — seed roles before assigning them."
            raise ValueError(msg)

        model = await self._db.get(UserModel, user.id)
        if model is None:
            msg = f"User {user.id} not found for update"
            raise ValueError(msg)
        model.role_id = role.id
        model.hospital_id = user.hospital_id
        model.is_active = user.is_active
        await self._db.flush()
        return self._to_entity(model, role_name=role.name)

    async def list_by_hospital(self, hospital_id: UUID) -> list[User]:
        stmt = (
            select(UserModel)
            .options(selectinload(UserModel.role))
            .where(UserModel.hospital_id == hospital_id)
        )
        result = await self._db.scalars(stmt)
        return [self._to_entity(model) for model in result]

    @staticmethod
    def _to_entity(model: UserModel, *, role_name: str | None = None) -> User:
        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            full_name=model.full_name,
            role_name=role_name or model.role.name,
            is_active=model.is_active,
            created_at=model.created_at,
            hospital_id=model.hospital_id,
        )
