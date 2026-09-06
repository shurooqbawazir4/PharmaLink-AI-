"""Pydantic v2 request/response models for the auth endpoints.

This is the only layer allowed to shape HTTP JSON — routers translate
between these and domain entities, never the other way around.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Mirrors the roles seeded by the initial migration (see
# docs/database.md) — constraining the literal here, at the API boundary,
# means an admin can never accidentally assign a role that doesn't exist.
AssignableRole = Literal["admin", "hospital_manager", "pharmacist", "viewer"]


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserAdminUpdateRequest(BaseModel):
    role_name: AssignableRole | None = None
    hospital_id: UUID | None = None
    clear_hospital: bool = Field(
        default=False, description="Explicitly unset hospital_id (for network-wide roles)."
    )


class UserRead(BaseModel):
    permissions: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role_name: str
    is_active: bool
    hospital_id: UUID | None
    created_at: datetime
