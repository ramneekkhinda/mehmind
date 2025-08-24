"""
MeshMind Budget Control Module

Budget tracking and LLM call management with cost controls.
"""

import asyncio
import time
import uuid
from typing import Any, Dict, Optional

from ..utils.errors import BudgetExceededError
from ..utils.logging import get_logger, log_budget_operation

logger = get_logger(__name__)


class BudgetContext:
    """Context manager for budget tracking and control."""

    def __init__(
        self,
        usd_cap: float = 10.0,
        rpm: int = 60,
        budget_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize budget context.

        Args:
            usd_cap: Maximum USD spending limit
            rpm: Requests per minute limit
            budget_id: Optional budget identifier
            tags: Optional metadata tags
        """
        self.usd_cap = usd_cap
        self.rpm = rpm
        self.budget_id = budget_id or f"budget_{uuid.uuid4().hex[:8]}"
        self.tags = tags or {}

        self.spent_usd = 0.0
        self.request_count = 0
        self.start_time = time.time()
        self._active = False

    def __enter__(self):
        """Enter budget context."""
        self._active = True
        logger.info(
            f"Budget context started: ${self.usd_cap} cap, {self.rpm} RPM",
            extra={
                "structured_data": {
                    "operation": "budget_start",
                    "budget_id": self.budget_id,
                    "usd_cap": self.usd_cap,
                    "rpm": self.rpm,
                    "tags": self.tags,
                }
            },
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit budget context."""
        self._active = False
        duration = time.time() - self.start_time

        logger.info(
            f"Budget context ended: ${self.spent_usd:.2f} spent, "
            f"{self.request_count} requests",
            extra={
                "structured_data": {
                    "operation": "budget_end",
                    "budget_id": self.budget_id,
                    "spent_usd": self.spent_usd,
                    "request_count": self.request_count,
                    "duration_seconds": duration,
                    "remaining_usd": self.usd_cap - self.spent_usd,
                }
            },
        )

    async def __aenter__(self):
        """Async enter budget context."""
        self._active = True
        logger.info(
            f"Budget context started: ${self.usd_cap} cap, " f"{self.rpm} RPM",
            extra={
                "structured_data": {
                    "operation": "budget_start",
                    "budget_id": self.budget_id,
                    "usd_cap": self.usd_cap,
                    "rpm": self.rpm,
                    "tags": self.tags,
                }
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async exit budget context."""
        self._active = False
        duration = time.time() - self.start_time

        logger.info(
            f"Budget context ended: ${self.spent_usd:.2f} spent, "
            f"{self.request_count} requests",
            extra={
                "structured_data": {
                    "operation": "budget_end",
                    "budget_id": self.budget_id,
                    "spent_usd": self.spent_usd,
                    "request_count": self.request_count,
                    "duration_seconds": duration,
                    "remaining_usd": self.usd_cap - self.spent_usd,
                }
            },
        )

    @property
    def remaining_usd(self) -> float:
        """Get remaining budget in USD."""
        return max(0.0, self.usd_cap - self.spent_usd)

    @property
    def remaining_rpm(self) -> int:
        """Get remaining requests per minute."""
        elapsed_minutes = (time.time() - self.start_time) / 60.0
        if elapsed_minutes >= 1.0:
            return self.rpm  # Reset after 1 minute
        return max(0, self.rpm - self.request_count)

    def consume(self, usd_amount: float, request_count: int = 1) -> None:
        """
        Consume budget resources.

        Args:
            usd_amount: USD amount to consume
            request_count: Number of requests to count

        Raises:
            BudgetExceededError: When budget limits are exceeded
        """
        if not self._active:
            raise RuntimeError("Budget context is not active")

        # Check USD limit
        if self.spent_usd + usd_amount > self.usd_cap:
            raise BudgetExceededError(
                message=(
                    f"Budget exceeded: ${self.spent_usd + usd_amount:.2f} > "
                    f"${self.usd_cap}"
                ),
                budget_id=self.budget_id,
                spent_amount=self.spent_usd + usd_amount,
                limit_amount=self.usd_cap,
            )

        # Check RPM limit
        if self.request_count + request_count > self.rpm:
            raise BudgetExceededError(
                message=(
                    f"RPM exceeded: {self.request_count + request_count} > "
                    f"{self.rpm}"
                ),
                budget_id=self.budget_id,
                spent_amount=self.spent_usd,
                limit_amount=self.rpm,
            )

        # Consume resources
        self.spent_usd += usd_amount
        self.request_count += request_count

        log_budget_operation(
            logger=logger,
            operation="consume",
            budget_id=self.budget_id,
            amount=usd_amount,
            remaining=self.remaining_usd,
            additional_data={
                "request_count": request_count,
                "total_requests": self.request_count,
            },
        )


async def call_model(
    prompt: str,
    budget_context: BudgetContext,
    provider: str = "openai",
    model: str = "gpt-3.5-turbo",
    max_tokens: int = 1000,
    temperature: float = 0.7,
) -> str:
    """
    Call an LLM model with budget tracking.

    Args:
        prompt: Input prompt for the model
        budget_context: Budget context for tracking costs
        provider: LLM provider (openai, anthropic, sim)
        model: Model name
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature

    Returns:
        Model response text

    Raises:
        BudgetExceededError: When budget limits are exceeded
    """
    # Simulate model call with cost estimation
    if provider == "sim":
        # Simulated provider for testing
        estimated_cost = 0.01  # $0.01 per call
        budget_context.consume(estimated_cost)

        # Simulate processing time
        await asyncio.sleep(0.1)

        return f"Simulated response to: {prompt[:50]}..."

    elif provider == "openai":
        # Estimate cost based on model and tokens
        if model == "gpt-3.5-turbo":
            cost_per_1k_tokens = 0.002
        elif model == "gpt-4":
            cost_per_1k_tokens = 0.03
        else:
            cost_per_1k_tokens = 0.002

        estimated_tokens = len(prompt.split()) + max_tokens
        estimated_cost = (estimated_tokens / 1000) * cost_per_1k_tokens

        budget_context.consume(estimated_cost)

        # Simulate OpenAI API call
        await asyncio.sleep(0.2)

        return f"OpenAI {model} response to: {prompt[:50]}..."

    elif provider == "anthropic":
        # Estimate cost for Anthropic models
        if model == "claude-3-sonnet":
            cost_per_1k_tokens = 0.015
        else:
            cost_per_1k_tokens = 0.008

        estimated_tokens = len(prompt.split()) + max_tokens
        estimated_cost = (estimated_tokens / 1000) * cost_per_1k_tokens

        budget_context.consume(estimated_cost)

        # Simulate Anthropic API call
        await asyncio.sleep(0.3)

        return f"Anthropic {model} response to: {prompt[:50]}..."

    else:
        raise ValueError(f"Unsupported provider: {provider}")
