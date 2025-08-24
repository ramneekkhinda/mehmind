"""
MeshMind Logging Configuration

Structured logging setup for MeshMind operations with proper formatting and levels.
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """Structured log formatter for consistent log output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured data."""
        # Add timestamp
        record.timestamp = datetime.utcnow().isoformat()

        # Add structured data if available
        if hasattr(record, "structured_data"):
            structured = record.structured_data
        else:
            structured = {}

        # Base log message
        log_entry = {
            "timestamp": record.timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add structured data
        if structured:
            log_entry["data"] = structured

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return str(log_entry)


def setup_logging(
    level: str = "INFO", enable_structured: bool = True, log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup MeshMind logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_structured: Enable structured logging format
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("meshmind")
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    if enable_structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "meshmind") -> logging.Logger:
    """Get a logger instance for the specified name."""
    return logging.getLogger(name)


def log_intent_preflight(
    logger: logging.Logger,
    intent_type: str,
    resource: str,
    decision: str,
    processing_time_ms: float,
    additional_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log intent preflight operation with structured data.

    Args:
        logger: Logger instance
        intent_type: Type of intent being preflighted
        resource: Resource identifier
        decision: Decision made (accept, deny, hold, replan)
        processing_time_ms: Processing time in milliseconds
        additional_data: Additional structured data
    """
    structured_data = {
        "operation": "intent_preflight",
        "intent_type": intent_type,
        "resource": resource,
        "decision": decision,
        "processing_time_ms": processing_time_ms,
    }

    if additional_data:
        structured_data.update(additional_data)

    logger.info(
        f"Intent preflight completed: {intent_type} -> {decision}",
        extra={"structured_data": structured_data},
    )


def log_budget_operation(
    logger: logging.Logger,
    operation: str,
    budget_id: str,
    amount: float,
    remaining: float,
    additional_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log budget operation with structured data.

    Args:
        logger: Logger instance
        operation: Budget operation type
        budget_id: Budget identifier
        amount: Amount involved in operation
        remaining: Remaining budget
        additional_data: Additional structured data
    """
    structured_data = {
        "operation": f"budget_{operation}",
        "budget_id": budget_id,
        "amount": amount,
        "remaining": remaining,
    }

    if additional_data:
        structured_data.update(additional_data)

    logger.info(
        f"Budget operation: {operation} - ${amount:.2f} (${remaining:.2f} remaining)",
        extra={"structured_data": structured_data},
    )


def log_effect_operation(
    logger: logging.Logger,
    effect_type: str,
    resource: str,
    idempotency_key: str,
    success: bool,
    additional_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log effect operation with structured data.

    Args:
        logger: Logger instance
        effect_type: Type of effect (http_post, email_send)
        resource: Resource identifier
        idempotency_key: Idempotency key used
        success: Whether operation was successful
        additional_data: Additional structured data
    """
    structured_data = {
        "operation": f"effect_{effect_type}",
        "resource": resource,
        "idempotency_key": idempotency_key,
        "success": success,
    }

    if additional_data:
        structured_data.update(additional_data)

    level = logging.INFO if success else logging.ERROR
    message = f"Effect operation: {effect_type} - {'SUCCESS' if success else 'FAILED'}"

    logger.log(level, message, extra={"structured_data": structured_data})
