"""Procurement-specific domain errors."""

from __future__ import annotations

from app.core.exceptions import BusinessRuleViolationError, NotFoundError


class SupplierNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(entity="Supplier", identifier=identifier)


class PurchaseOrderNotFoundError(NotFoundError):
    def __init__(self, identifier: str) -> None:
        super().__init__(entity="PurchaseOrder", identifier=identifier)


class InvalidPurchaseOrderStateError(BusinessRuleViolationError):
    def __init__(self, *, current_status: str, action: str) -> None:
        self.current_status = current_status
        self.action = action
        super().__init__(f"Cannot {action} a purchase order that is currently '{current_status}'.")


class NoSupplierAvailableError(BusinessRuleViolationError):
    def __init__(self, medicine_id: str) -> None:
        super().__init__(f"No active supplier available to recommend an order for '{medicine_id}'.")
