"""
MeshMind LangGraph Integration Decorators

Decorators and utilities for integrating MeshMind safety controls with LangGraph workflows.
"""

import functools
import time
from typing import Callable, Any, Dict, Optional, Tuple, Union
from contextlib import asynccontextmanager

from langgraph.graph import StateGraph, END

from ..core.intents import preflight_intent
from ..utils.errors import PolicyDeniedError, RefereeConnectionError
from ..utils.logging import get_logger

logger = get_logger(__name__)


def wrap_node(
    intent_func: Optional[Callable[[Dict[str, Any]], Tuple[str, Dict[str, Any]]]] = None
) -> Callable[[Callable], Callable]:
    """
    Decorator to wrap LangGraph nodes with intent preflight.
    
    This decorator adds safety controls to LangGraph nodes by preflighting
    intents before node execution. It handles various decision outcomes
    including accept, deny, hold, and replan scenarios.
    
    Args:
        intent_func: Function that generates intent from state.
                     Should return (intent_type, intent_payload) tuple.
                     If None, the node runs without preflight.
    
    Returns:
        Decorated function with intent preflight capabilities
        
    Raises:
        PolicyDeniedError: When intent is denied by policy
        RefereeConnectionError: When referee service is unavailable
        
    Example:
        @wrap_node(lambda s: ("email.send", {
            "resource": f"customer:{s['email']}",
            "author": "support-agent"
        }))
        async def send_email(state):
            return await email_service.send(state["email"])
    """
    
    def decorator(node_func: Callable) -> Callable:
        @functools.wraps(node_func)
        async def wrapped_node(state: Dict[str, Any]) -> Dict[str, Any]:
            # If no intent function provided, run node without preflight
            if intent_func is None:
                return await node_func(state)
            
            start_time = time.time()
            
            # Generate intent from state
            try:
                intent_type, intent_payload = intent_func(state)
            except Exception as e:
                logger.warning(
                    "Intent generation failed",
                    extra={
                        "structured_data": {
                            "operation": "intent_generation",
                            "node": node_func.__name__,
                            "error": str(e),
                            "state_keys": list(state.keys())
                        }
                    }
                )
                
                # Fallback to running node without preflight
                if hasattr(state, 'get') and state.get('meshmind_graceful_degradation', True):
                    logger.info(f"Proceeding with node execution despite intent generation failure")
                    return await node_func(state)
                else:
                    raise
            
            # Preflight the intent
            try:
                decision = await preflight_intent(intent_type, intent_payload)
                processing_time_ms = (time.time() - start_time) * 1000
                
                logger.debug(
                    f"Intent preflight completed in {processing_time_ms:.2f}ms",
                    extra={
                        "structured_data": {
                            "operation": "intent_preflight",
                            "intent_type": intent_type,
                            "resource": intent_payload.get("resource"),
                            "decision": decision.get("action"),
                            "processing_time_ms": processing_time_ms
                        }
                    }
                )
                
                # Handle decision outcomes
                if decision["action"] == "accept":
                    # Intent accepted, proceed with node execution
                    result = await node_func(state)
                    
                    # If this was a hold, confirm it after successful execution
                    if decision.get("hold_id"):
                        from ..core.holds import confirm_hold
                        await confirm_hold(decision["hold_id"])
                    
                    return result
                
                elif decision["action"] == "hold":
                    # Hold granted, proceed with node execution
                    result = await node_func(state)
                    
                    # Confirm the hold after successful execution
                    if decision.get("hold_id"):
                        from ..core.holds import confirm_hold
                        await confirm_hold(decision["hold_id"])
                    
                    return result
                
                elif decision["action"] == "replan":
                    # Intent needs replanning, return replan state
                    replan_count = state.get("replan_count", 0) + 1
                    
                    logger.info(
                        f"Intent requires replanning (attempt {replan_count})",
                        extra={
                            "structured_data": {
                                "operation": "intent_replan",
                                "intent_type": intent_type,
                                "resource": intent_payload.get("resource"),
                                "reason": decision.get("reason"),
                                "replan_count": replan_count
                            }
                        }
                    )
                    
                    return {
                        **state,
                        "replan": True,
                        "replan_reason": decision["reason"],
                        "replan_suggestions": decision.get("suggested", []),
                        "replan_count": replan_count,
                        "last_intent_type": intent_type,
                        "last_intent_resource": intent_payload.get("resource")
                    }
                
                elif decision["action"] == "deny":
                    # Intent denied, raise exception
                    logger.warning(
                        f"Intent denied: {decision.get('reason', 'unknown')}",
                        extra={
                            "structured_data": {
                                "operation": "intent_denied",
                                "intent_type": intent_type,
                                "resource": intent_payload.get("resource"),
                                "reason": decision.get("reason"),
                                "details": decision.get("why")
                            }
                        }
                    )
                    
                    raise PolicyDeniedError(
                        message=f"Intent denied: {decision.get('reason', 'unknown')}",
                        intent_type=intent_type,
                        resource=intent_payload.get("resource"),
                        reason=decision.get("reason"),
                        details=decision
                    )
                
                else:
                    # Unknown action, proceed with caution
                    logger.warning(
                        f"Unknown decision action: {decision['action']}",
                        extra={
                            "structured_data": {
                                "operation": "unknown_decision",
                                "intent_type": intent_type,
                                "resource": intent_payload.get("resource"),
                                "decision": decision
                            }
                        }
                    )
                    
                    # Default to running the node
                    return await node_func(state)
                    
            except (PolicyDeniedError, RefereeConnectionError):
                # Re-raise policy and connection errors
                raise
            except Exception as e:
                # Handle other preflight errors
                processing_time_ms = (time.time() - start_time) * 1000
                
                logger.warning(
                    "Intent preflight failed",
                    extra={
                        "structured_data": {
                            "operation": "intent_preflight_error",
                            "intent_type": intent_type,
                            "resource": intent_payload.get("resource"),
                            "error": str(e),
                            "processing_time_ms": processing_time_ms
                        }
                    }
                )
                
                # Fallback to running node without preflight
                if hasattr(state, 'get') and state.get('meshmind_graceful_degradation', True):
                    logger.info("Graceful degradation: proceeding without preflight")
                    return await node_func(state)
                else:
                    raise
        
        return wrapped_node
    
    return decorator


def create_intent_node(
    intent_type: str, 
    intent_payload_func: Callable[[Dict[str, Any]], Dict[str, Any]]
) -> Callable:
    """
    Create a node that only handles intent preflight.
    
    This is useful for creating dedicated intent nodes in the graph
    that can be used for conditional routing based on intent decisions.
    
    Args:
        intent_type: Type of intent to preflight
        intent_payload_func: Function that generates intent payload from state
        
    Returns:
        Node function that performs intent preflight
        
    Example:
        intent_node = create_intent_node(
            "email.send",
            lambda s: {"resource": f"customer:{s['email']}", "author": "agent"}
        )
        workflow.add_node("preflight", intent_node)
    """
    
    async def intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Node that performs intent preflight."""
        try:
            # Generate intent payload from state
            intent_payload = intent_payload_func(state)
            
            # Preflight the intent
            decision = await preflight_intent(intent_type, intent_payload)
            
            logger.debug(
                f"Intent node preflight completed",
                extra={
                    "structured_data": {
                        "operation": "intent_node_preflight",
                        "intent_type": intent_type,
                        "resource": intent_payload.get("resource"),
                        "decision": decision.get("action")
                    }
                }
            )
            
            # Return decision in state
            return {
                **state,
                "intent_decision": decision,
                "intent_type": intent_type,
                "intent_payload": intent_payload
            }
            
        except Exception as e:
            logger.error(
                f"Intent node preflight failed",
                extra={
                    "structured_data": {
                        "operation": "intent_node_error",
                        "intent_type": intent_type,
                        "error": str(e)
                    }
                }
            )
            raise
    
    return intent_node


def create_conditional_edge(
    decision_key: str = "intent_decision",
    default_node: str = "proceed"
) -> Callable:
    """
    Create a conditional edge based on intent decision.
    
    This function creates a conditional routing function that can be used
    with LangGraph's conditional edges to route based on intent decisions.
    
    Args:
        decision_key: Key in state containing the decision
        default_node: Default node to route to if decision is unclear
        
    Returns:
        Function that returns the next node based on decision
        
    Example:
        conditional_edge = create_conditional_edge()
        workflow.add_edge("preflight", conditional_edge)
        workflow.add_edge("proceed", "send_email")
        workflow.add_edge("replan", "replan_strategy")
    """
    
    def conditional_edge(state: Dict[str, Any]) -> str:
        """Return next node based on intent decision."""
        decision = state.get(decision_key, {})
        action = decision.get("action", "accept")
        
        logger.debug(
            f"Conditional edge routing based on decision",
            extra={
                "structured_data": {
                    "operation": "conditional_edge",
                    "decision_action": action,
                    "next_node": action if action in ["proceed", "replan"] else default_node
                }
            }
            )
        
        if action in ["accept", "hold"]:
            return "proceed"
        elif action == "replan":
            return "replan"
        elif action == "deny":
            return END
        else:
            return default_node
    
    return conditional_edge


@asynccontextmanager
async def intent_context(
    intent_type: str,
    payload: Dict[str, Any]
):
    """
    Context manager for intent preflight.
    
    This context manager can be used to wrap code blocks that need
    intent preflight without using the decorator pattern.
    
    Args:
        intent_type: Type of intent to preflight
        payload: Intent payload
        
    Yields:
        Decision from referee service
        
    Raises:
        PolicyDeniedError: When intent is denied
        RefereeConnectionError: When referee service is unavailable
    """
    try:
        decision = await preflight_intent(intent_type, payload)
        
        if decision["action"] == "deny":
            raise PolicyDeniedError(
                message=f"Intent denied: {decision.get('reason', 'unknown')}",
                intent_type=intent_type,
                resource=payload.get("resource"),
                reason=decision.get("reason")
            )
        
        yield decision
        
        # Confirm hold if present
        if decision.get("hold_id") and decision["action"] in ["accept", "hold"]:
            from ..core.holds import confirm_hold
            await confirm_hold(decision["hold_id"])
            
    except Exception:
        # Re-raise any exceptions
        raise
