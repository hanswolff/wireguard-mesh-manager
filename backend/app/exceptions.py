"""Custom exceptions for the application."""

from __future__ import annotations

from typing import Any


class WireGuardError(Exception):
    """Base exception for WireGuard mesh manager."""

    def __init__(self, message: str, detail: Any = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class ResourceNotFoundError(WireGuardError):
    """Raised when a resource is not found."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(f"{resource_type} with ID {resource_id} not found")
        self.resource_type = resource_type
        self.resource_id = resource_id


class ResourceConflictError(WireGuardError):
    """Raised when a resource conflicts with existing data."""

    def __init__(self, message: str):
        super().__init__(message)


class BusinessRuleViolationError(WireGuardError):
    """Raised when a business rule is violated."""

    def __init__(self, rule: str, message: str):
        super().__init__(f"Business rule violation: {message}")
        self.rule = rule
