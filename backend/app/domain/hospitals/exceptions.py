"""Hospital-specific domain errors."""

from __future__ import annotations

from app.core.exceptions import AlreadyExistsError, NotFoundError


class HospitalNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(entity="Hospital", identifier=identifier)


class HospitalCodeAlreadyExistsError(AlreadyExistsError):
    def __init__(self, code: str) -> None:
        super().__init__(entity="Hospital", field="code", value=code)
