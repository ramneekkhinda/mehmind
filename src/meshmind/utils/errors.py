"""
MeshMind Error Types

Custom exception classes for MeshMind operations with structured error information.
"""

from typing import Any, Dict, Optional


class MeshMindError(Exception):
    """Base exception for all MeshMind errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class PolicyDeniedError(MeshMindError):
    """Raised when an intent is denied by policy enforcement."""

    def __init__(
        self,
        message: str,
        intent_type: Optional[str] = None,
        resource: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "POLICY_DENIED", details)
        self.intent_type = intent_type
        self.resource = resource
        self.reason = reason


class RefereeConnectionError(MeshMindError):
    """Raised when unable to connect to the referee service."""

    def __init__(
        self,
        message: str,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "REFEREE_CONNECTION_ERROR", details)
        self.base_url = base_url
        self.timeout = timeout


class IdempotencyConflictError(MeshMindError):
    """Raised when an idempotency key conflict is detected."""

    def __init__(
        self,
        message: str,
        idempotency_key: Optional[str] = None,
        resource_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "IDEMPOTENCY_CONFLICT", details)
        self.idempotency_key = idempotency_key
        self.resource_type = resource_type


class BudgetExceededError(MeshMindError):
    """Raised when budget limits are exceeded."""

    def __init__(
        self,
        message: str,
        budget_id: Optional[str] = None,
        spent_amount: Optional[float] = None,
        limit_amount: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "BUDGET_EXCEEDED", details)
        self.budget_id = budget_id
        self.spent_amount = spent_amount
        self.limit_amount = limit_amount


class HoldConflictError(MeshMindError):
    """Raised when a hold request conflicts with existing holds."""

    def __init__(
        self,
        message: str,
        resource: Optional[str] = None,
        existing_hold_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "HOLD_CONFLICT", details)
        self.resource = resource
        self.existing_hold_id = existing_hold_id


class LockAcquisitionError(MeshMindError):
    """Raised when unable to acquire a resource lock."""

    def __init__(
        self,
        message: str,
        resource: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "LOCK_ACQUISITION_ERROR", details)
        self.resource = resource
        self.ttl_seconds = ttl_seconds
