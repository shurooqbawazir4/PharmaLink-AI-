"""Medicine-specific domain errors."""

from __future__ import annotations

from app.core.exceptions import NotFoundError


class MedicineNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(entity="Medicine", identifier=identifier)
