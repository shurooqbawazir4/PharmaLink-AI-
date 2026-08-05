"""Transfer-specific domain errors."""

from __future__ import annotations

from app.core.exceptions import BusinessRuleViolationError, NotFoundError


class TransferNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(entity="Transfer", identifier=identifier)


class InvalidTransferStateError(BusinessRuleViolationError):
    def __init__(self, *, current_status: str, action: str) -> None:
        self.current_status = current_status
        self.action = action
        super().__init__(f"Cannot {action} a transfer that is currently '{current_status}'.")


class InsufficientAvailableStockError(BusinessRuleViolationError):
    def __init__(self, *, available: int, requested: int) -> None:
        self.available = available
        self.requested = requested
        super().__init__(
            f"Source hospital only has {available} units available "
            f"(above safety stock) but {requested} were requested."
        )


class SameHospitalTransferError(BusinessRuleViolationError):
    def __init__(self) -> None:
        super().__init__("Source and destination hospitals must be different.")
