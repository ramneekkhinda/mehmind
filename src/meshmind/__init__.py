"""
MeshMind: Production Safety for LangGraph Agents

MeshMind provides runtime safety and cost control for LangGraph-based AI agents.
It enables intent preflight, resource locking, budget control, and idempotent effects
to prevent production disasters in multi-agent systems.

Key Features:
- Intent preflight with policy enforcement
- Semantic resource locking and holds
- Budget and rate limiting controls
- Idempotent HTTP and email effects
- Graceful degradation and error handling

Example:
    from meshmind.langgraph import wrap_node
    
    @wrap_node(lambda s: ("email.send", {"resource": f"customer:{s['email']}"}))
    async def send_email(state):
        return await email_service.send(state["email"])
"""

__version__ = "0.1.0"
__author__ = "MeshMind Team"
__email__ = "team@meshmind.ai"

from .core.intents import preflight_intent
from .core.budget import BudgetContext, call_model
from .core.effects import http_post, email_send
from .langgraph.decorators import wrap_node
from .utils.errors import (
    MeshMindError,
    PolicyDeniedError,
    RefereeConnectionError,
    IdempotencyConflictError,
    BudgetExceededError
)

__all__ = [
    # Core functionality
    "preflight_intent",
    "BudgetContext",
    "call_model",
    "http_post",
    "email_send",
    
    # LangGraph integration
    "wrap_node",
    
    # Error types
    "MeshMindError",
    "PolicyDeniedError", 
    "RefereeConnectionError",
    "IdempotencyConflictError",
    "BudgetExceededError",
    
    # Version
    "__version__"
]
