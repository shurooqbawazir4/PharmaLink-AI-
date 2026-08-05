"""Domain-level exception hierarchy and their HTTP translation.

Domain and application layers raise these (or module-specific subclasses of
them — see e.g. `app/domain/hospitals/exceptions.py`) without knowing
anything about HTTP. `register_exception_handlers` is the single place that
maps them to status codes, so no router ever needs a try/except.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class for all domain/business-rule errors."""


class NotFoundError(DomainError):
    def __init__(self, entity: str, identifier: str | UUID):
        self.entity = entity
        self.identifier = identifier
        super().__init__(f"{entity} with id '{identifier}' was not found.")


class AlreadyExistsError(DomainError):
    def __init__(self, entity: str, field: str, value: str):
        self.entity = entity
        self.field = field
        self.value = value
        super().__init__(f"{entity} with {field} '{value}' already exists.")


class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__("Invalid email or password.")


class UnauthorizedError(DomainError):
    """Missing or invalid authentication."""


class ForbiddenError(DomainError):
    """Authenticated, but not permitted to perform this action."""


class BusinessRuleViolationError(DomainError):
    """A domain invariant was violated (e.g. negative stock, bad state transition)."""


_STATUS_MAP: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    AlreadyExistsError: status.HTTP_409_CONFLICT,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
    ForbiddenError: status.HTTP_403_FORBIDDEN,
    BusinessRuleViolationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def register_exception_handlers(app: FastAPI) -> None:
    """Wire every `DomainError` subclass to a consistent JSON error shape."""

    @app.exception_handler(DomainError)
    async def _handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status_code = status.HTTP_400_BAD_REQUEST
        for exc_type, mapped_status in _STATUS_MAP.items():
            if isinstance(exc, exc_type):
                status_code = mapped_status
                break
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc), "error_type": type(exc).__name__},
        )
