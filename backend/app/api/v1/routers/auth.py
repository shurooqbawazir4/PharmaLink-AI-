"""Auth endpoints: register, login, refresh, current-user lookup."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import CurrentUser, require_role
from app.api.v1.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserAdminUpdateRequest,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)
from app.application.auth.service import AuthService
from app.core.di import get_auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, auth_service: AuthServiceDep) -> UserRead:
    user = await auth_service.register(
        email=payload.email, password=payload.password, full_name=payload.full_name
    )
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLoginRequest, auth_service: AuthServiceDep) -> TokenResponse:
    _user, tokens = await auth_service.authenticate(email=payload.email, password=payload.password)
    return TokenResponse(**asdict(tokens))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshTokenRequest, auth_service: AuthServiceDep) -> TokenResponse:
    tokens = await auth_service.refresh(payload.refresh_token)
    return TokenResponse(**asdict(tokens))


@router.get("/me", response_model=UserRead)
async def get_me(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch(
    "/users/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(require_role("admin"))],
)
async def admin_update_user(
    user_id: UUID, payload: UserAdminUpdateRequest, auth_service: AuthServiceDep
) -> UserRead:
    """Promote/demote a role and/or (re)assign a hospital — admin-only.
    The one write path a fresh registration can't reach on its own."""
    user = await auth_service.admin_update(
        user_id,
        role_name=payload.role_name,
        hospital_id=payload.hospital_id,
        clear_hospital=payload.clear_hospital,
    )
    return UserRead.model_validate(user)
