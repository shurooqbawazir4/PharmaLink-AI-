"""Auth-specific domain errors — thin subclasses of the generic core ones."""

from __future__ import annotations

from app.core.exceptions import AlreadyExistsError, NotFoundError


class UserNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(entity="User", identifier=identifier)


class UserAlreadyExistsError(AlreadyExistsError):
    def __init__(self, email: str) -> None:
        super().__init__(entity="User", field="email", value=email)
