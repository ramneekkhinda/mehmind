"""
Ghost-Run Decorators: Interceptors for MeshMind functions during simulation.
"""

import functools
import time
from typing import Any, Dict

from ..utils.logging import get_logger
from .reports import ConflictReport

logger = get_logger(__name__)


def ghost_call_model(func):
    """Decorator to intercept call_model during ghost simulation."""

    @functools.wraps(func)
    async def wrapper(prompt: str, budget_context, **kwargs):
        # Check if we're in ghost mode
        if hasattr(budget_context, "_ghost_mode") and budget_context._ghost_mode:
            return await _ghost_call_model(prompt, budget_context, **kwargs)

        # Normal execution
        return await func(prompt, budget_context, **kwargs)

    return wrapper


def ghost_http_post(func):
    """Decorator to intercept http_post during ghost simulation."""

    @functools.wraps(func)
    async def wrapper(url: str, data: Dict[str, Any], **kwargs):
        # Check if we're in ghost mode
        if kwargs.get("_ghost_mode"):
            return await _ghost_http_post(url, data, **kwargs)

        # Normal execution
        return await func(url, data, **kwargs)

    return wrapper


def ghost_email_send(func):
    """Decorator to intercept email_send during ghost simulation."""

    @functools.wraps(func)
    async def wrapper(contact_id: str, body: str, subject: str, **kwargs):
        # Check if we're in ghost mode
        if kwargs.get("_ghost_mode"):
            return await _ghost_email_send(contact_id, body, subject, **kwargs)

        # Normal execution
        return await func(contact_id, body, subject, **kwargs)

    return wrapper


def ghost_preflight_intent(func):
    """Decorator to intercept preflight_intent during ghost simulation."""

    @functools.wraps(func)
    async def wrapper(intent_type: str, payload: Dict[str, Any]):
        # Check if we're in ghost mode
        if payload.get("_ghost_mode"):
            return await _ghost_preflight_intent(intent_type, payload)

        # Normal execution
        return await func(intent_type, payload)

    return wrapper


async def _ghost_call_model(prompt: str, budget_context, **kwargs):
    """Ghost implementation of call_model."""

    # Estimate tokens and cost
    estimated_tokens = _estimate_tokens(prompt, kwargs.get("max_tokens", 1000))
    _estimated_cost = _estimate_llm_cost(
        provider=kwargs.get("provider", "openai"),
        model=kwargs.get("model", "gpt-3.5-turbo"),
        input_tokens=estimated_tokens,
        output_tokens=kwargs.get("max_tokens", 1000),
    )

    # Simulate processing time
    await _ghost_sleep(0.1)

    # Update ghost state
    if hasattr(budget_context, "_ghost_state"):
        budget_context._ghost_state.total_tokens += estimated_tokens
        budget_context._ghost_state.llm_calls += 1

    # Return simulated response
    return f"[GHOST] {kwargs.get('provider', 'openai')} response to: {prompt[:50]}..."


async def _ghost_http_post(url: str, data: Dict[str, Any], **kwargs):
    """Ghost implementation of http_post."""

    # Estimate cost (typically very low for API calls)
    _estimated_cost = 0.001  # $0.001 per API call

    # Check for resource conflicts
    conflicts = []
    idempotency_key = kwargs.get("idempotency_key")
    if idempotency_key:
        # Simulate idempotency check
        conflicts.extend(_check_idempotency_conflicts(idempotency_key, "http_post"))

    # Simulate processing time
    await _ghost_sleep(0.05)

    # Update ghost state
    if kwargs.get("_ghost_state"):
        kwargs["_ghost_state"].api_calls += 1

    # Return simulated response
    return {
        "id": f"ghost_response_{int(time.time())}",
        "status": "success",
        "data": {"message": "Ghost API call successful"},
    }


async def _ghost_email_send(contact_id: str, body: str, subject: str, **kwargs):
    """Ghost implementation of email_send."""

    # Estimate cost (typically very low for emails)
    _estimated_cost = 0.0001  # $0.0001 per email

    # Check for frequency cap violations
    conflicts = []
    conflicts.extend(_check_frequency_caps(f"contact:{contact_id}", "email"))

    # Check for idempotency conflicts
    idempotency_key = kwargs.get("idempotency_key")
    if idempotency_key:
        conflicts.extend(_check_idempotency_conflicts(idempotency_key, "email_send"))

    # Simulate processing time
    await _ghost_sleep(0.02)

    # Update ghost state
    if kwargs.get("_ghost_state"):
        kwargs["_ghost_state"].effects_count += 1

    # Return simulated response
    return {
        "message_id": f"ghost_email_{int(time.time())}",
        "status": "sent",
        "recipient": contact_id,
    }


async def _ghost_preflight_intent(intent_type: str, payload: Dict[str, Any]):
    """Ghost implementation of preflight_intent."""

    # Simulate intent preflight decision
    resource = payload.get("resource", "unknown")
    author = payload.get("author", "unknown")

    # Check for resource conflicts
    conflicts = []
    conflicts.extend(_check_resource_locks(resource, author))
    conflicts.extend(_check_frequency_caps(intent_type, author))

    # Simulate processing time
    await _ghost_sleep(0.01)

    # Return simulated decision
    if conflicts:
        return {
            "action": "deny",
            "reason": "conflicts_detected",
            "why": f"Ghost simulation detected {len(conflicts)} conflicts",
            "evidence": {"conflicts": [c.__dict__ for c in conflicts]},
        }
    else:
        return {
            "action": "accept",
            "reason": "no_conflicts",
            "why": "Ghost simulation found no conflicts",
            "evidence": {},
        }


def _estimate_tokens(text: str, max_output_tokens: int = 1000) -> int:
    """Estimate token count for text."""
    # Simple estimation: ~4 characters per token
    return len(text) // 4 + max_output_tokens


def _estimate_llm_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> float:
    """Estimate cost for LLM call based on provider and model."""

    # Pricing per 1K tokens (approximate)
    pricing = {
        "openai": {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        },
        "anthropic": {
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        },
        "sim": {"default": {"input": 0.001, "output": 0.001}},
    }

    # Get pricing for provider/model
    provider_pricing = pricing.get(provider, pricing["sim"])
    model_pricing = provider_pricing.get(
        model, provider_pricing.get("default", {"input": 0.001, "output": 0.001})
    )

    # Calculate cost
    input_cost = (input_tokens / 1000) * model_pricing["input"]
    output_cost = (output_tokens / 1000) * model_pricing["output"]

    return input_cost + output_cost


def _check_resource_locks(resource: str, author: str) -> list:
    """Check for resource lock conflicts."""
    conflicts = []

    # This would integrate with the actual lock manager in a real implementation
    # For now, simulate some common conflicts

    if "customer:" in resource and author != "primary-agent":
        conflicts.append(
            ConflictReport(
                conflict_type="resource_lock",
                resource=resource,
                node_name="ghost_simulation",
                step_number=0,
                severity="medium",
                description=f"Resource {resource} may be locked by another agent",
                suggested_fix="Use resource hold request before accessing",
            )
        )

    return conflicts


def _check_frequency_caps(action_type: str, author: str) -> list:
    """Check for frequency cap violations."""
    conflicts = []

    # Simulate frequency cap checks
    if "email" in action_type:
        # Check if too many emails sent recently
        conflicts.append(
            ConflictReport(
                conflict_type="frequency_cap",
                resource=f"contact:{author}",
                node_name="ghost_simulation",
                step_number=0,
                severity="low",
                description=f"Email frequency cap may be exceeded for {author}",
                suggested_fix="Check frequency cap settings and timing",
            )
        )

    return conflicts


def _check_idempotency_conflicts(idempotency_key: str, operation_type: str) -> list:
    """Check for idempotency conflicts."""
    conflicts = []

    # Simulate idempotency checks
    if "duplicate" in idempotency_key.lower():
        conflicts.append(
            ConflictReport(
                conflict_type="idempotency_conflict",
                resource=idempotency_key,
                node_name="ghost_simulation",
                step_number=0,
                severity="high",
                description=f"Idempotency conflict detected for {operation_type}",
                suggested_fix="Use unique idempotency keys for each operation",
            )
        )

    return conflicts


async def _ghost_sleep(duration: float):
    """Simulate processing time during ghost execution."""
    # Use a very short sleep to simulate processing without blocking
    import asyncio

    await asyncio.sleep(duration * 0.1)  # Scale down for faster simulation


# Ghost BudgetContext
class GhostBudgetContext:
    """Ghost version of BudgetContext for simulation."""

    def __init__(self, usd_cap: float = 10.0, rpm: int = 60, **kwargs):
        self.usd_cap = usd_cap
        self.rpm = rpm
        self.spent_usd = 0.0
        self.request_count = 0
        self._ghost_mode = True
        self._ghost_state = kwargs.get("_ghost_state")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def consume(self, usd_amount: float, request_count: int = 1):
        """Consume budget in ghost mode."""
        self.spent_usd += usd_amount
        self.request_count += request_count

        if self._ghost_state:
            self._ghost_state.budget_consumed += usd_amount

    @property
    def remaining_usd(self) -> float:
        return max(0, self.usd_cap - self.spent_usd)

    @property
    def remaining_rpm(self) -> int:
        return max(0, self.rpm - self.request_count)
