"""Password hashing and JWT issuance/verification.

Kept framework-agnostic (no FastAPI imports) so it can be unit tested and
reused by the `AuthService` without pulling in the web layer.

Hashes with `bcrypt` directly rather than via `passlib`: passlib 1.7.4 is
unmaintained and its backend version-probe crashes against bcrypt>=4.1
(missing `__about__.__version__`), which then misfires a bogus self-test
and raises spuriously on every hash — a known, still-unfixed break.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

import bcrypt
import jwt

from app.core.config import settings

# bcrypt silently ignores bytes beyond 72 — truncate explicitly so long
# passwords fail loudly in review rather than being quietly weakened.
_MAX_PASSWORD_BYTES = 72


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(Exception):
    """Raised when a JWT is malformed, expired, or of the wrong type."""


def hash_password(plain_password: str) -> str:
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > _MAX_PASSWORD_BYTES:
        msg = f"Password must be at most {_MAX_PASSWORD_BYTES} bytes when UTF-8 encoded."
        raise ValueError(msg)
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:_MAX_PASSWORD_BYTES]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def _create_token(*, subject: UUID, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    return _create_token(
        subject=user_id,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: UUID) -> str:
    return _create_token(
        subject=user_id,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, *, expected_type: TokenType) -> UUID:
    """Decode a JWT and return the subject (user id) if valid and of the right type.

    Raises `InvalidTokenError` for anything that isn't a currently-valid
    access/refresh token — callers translate that into a 401.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Token is invalid or expired.") from exc

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"Expected a '{expected_type.value}' token.")

    try:
        return UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("Token subject is missing or malformed.") from exc
