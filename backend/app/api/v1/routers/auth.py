"""Auth endpoints: register, login, refresh, current-user lookup."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps import CurrentUser
from app.api.v1.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
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
