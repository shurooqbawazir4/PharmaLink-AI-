"""Auth use cases: registration, login, token refresh.

Pure business logic — depends only on `UserRepository` (a `Protocol`), the
framework-free `app.core.security` helpers, and the `User`/`Role` domain
entities. Knows nothing about HTTP or SQLAlchemy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.exceptions import InvalidCredentialsError
from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domain.auth.entities import User
from app.domain.auth.exceptions import UserAlreadyExistsError, UserNotFoundError
from app.domain.auth.repository import UserRepository

# Roles are intentionally open-ended strings backed by `roles.permissions`
# (JSONB) rather than a hardcoded enum, so new roles don't require a code
# change — this is the set seeded by the initial migration.
DEFAULT_ROLE = "viewer"


@dataclass(slots=True, frozen=True)
class AuthTokens:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        role_name: str = DEFAULT_ROLE,
        hospital_id: UUID | None = None,
    ) -> User:
        if await self._users.get_by_email(email) is not None:
            raise UserAlreadyExistsError(email)

        user = User(
            id=uuid4(),
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role_name=role_name,
            is_active=True,
            created_at=datetime.now(UTC),
            hospital_id=hospital_id,
        )
        return await self._users.create(user)

    async def authenticate(self, *, email: str, password: str) -> tuple[User, AuthTokens]:
        user = await self._users.get_by_email(email)
        password_ok = user is not None and verify_password(password, user.hashed_password)
        if user is None or not user.is_active or not password_ok:
            raise InvalidCredentialsError()

        return user, AuthTokens(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def refresh(self, refresh_token: str) -> AuthTokens:
        try:
            user_id = decode_token(refresh_token, expected_type=TokenType.REFRESH)
        except InvalidTokenError as exc:
            raise InvalidCredentialsError() from exc

        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidCredentialsError()

        return AuthTokens(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def admin_update(
        self,
        user_id: UUID,
        *,
        role_name: str | None = None,
        hospital_id: UUID | None = None,
        clear_hospital: bool = False,
    ) -> User:
        """Promote/demote a user's role and/or (re)assign their hospital —
        the one write path missing from Milestone A's Auth module, and what
        Milestone B's hospital-scoped RBAC (`require_own_hospital_or_admin`)
        needs to actually be exercisable: registration alone can only ever
        produce a hospital-less `viewer`. Admin-only at the router layer.
        `clear_hospital=True` explicitly unsets hospital_id (network-wide
        admins have none); a plain `None` leaves it unchanged."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))

        if role_name is not None:
            user.role_name = role_name
        if clear_hospital:
            user.hospital_id = None
        elif hospital_id is not None:
            user.hospital_id = hospital_id

        return await self._users.update(user)

    async def get_current_user(self, access_token: str) -> User:
        try:
            user_id = decode_token(access_token, expected_type=TokenType.ACCESS)
        except InvalidTokenError as exc:
            raise InvalidCredentialsError() from exc

        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            # A structurally valid token for a deleted/deactivated user is an
            # auth failure, not a 404 — the caller has no "user id" to look up.
            raise InvalidCredentialsError()
        return user
