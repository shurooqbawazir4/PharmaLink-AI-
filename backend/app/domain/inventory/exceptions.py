"""Inventory-specific domain errors."""

from __future__ import annotations

from app.core.exceptions import BusinessRuleViolationError, NotFoundError


class InventoryBatchNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(entity="InventoryBatch", identifier=identifier)


class InsufficientStockError(BusinessRuleViolationError):
    def __init__(self, *, available: int, requested: int) -> None:
        self.available = available
        self.requested = requested
        super().__init__(
            f"Requested quantity ({requested}) exceeds available stock ({available})."
        )
