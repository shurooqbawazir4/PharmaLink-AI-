"""HTTP-layer auth dependencies: bearer-token decoding and RBAC gating.

These are the only place in the codebase that know about `Authorization`
headers — everything downstream (services, repositories) just receives a
`User` domain entity.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.auth.service import AuthService
from app.core.di import get_auth_service
from app.core.exceptions import ForbiddenError
from app.domain.auth.entities import User

_bearer_scheme = HTTPBearer(description="Access token issued by /auth/login")


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    user = await auth_service.get_current_user(credentials.credentials)
    # Stashed for AuditLogMiddleware (app.core.logging), which runs outside
    # the Depends graph and can't otherwise learn who made the request.
    request.state.user_id = user.id
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: str) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Dependency factory: `Depends(require_role("admin", "hospital_manager"))`.

    Declarative RBAC at the router level rather than scattered checks in
    services — `"admin"` always passes regardless of the list, matching the
    "*" wildcard permission convention used by `roles.permissions`.
    """

    async def _check(user: CurrentUser) -> User:
        if user.role_name == "admin" or user.role_name in allowed_roles:
            return user
        raise ForbiddenError(
            f"Role '{user.role_name}' is not permitted to perform this action "
            f"(requires one of: {', '.join(allowed_roles)})."
        )

    return _check
