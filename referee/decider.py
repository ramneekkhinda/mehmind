"""MeshMind Decision Engine."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from opentelemetry import trace
from .schemas import Intent, Decision, HoldResponse
from .locks import LockManager
from .holds import HoldManager
from .budget import BudgetManager
from .policy import PolicyManager
from .store import Store

tracer = trace.get_tracer(__name__)


class Decider:
    """Core decision engine for MeshMind referee service."""
    
    def __init__(
        self,
        lock_manager: LockManager,
        hold_manager: HoldManager,
        budget_manager: BudgetManager,
        policy_manager: PolicyManager,
        store: Store
    ):
        self.lock_manager = lock_manager
        self.hold_manager = hold_manager
        self.budget_manager = budget_manager
        self.policy_manager = policy_manager
        self.store = store
        self.REPLAN_LIMIT = 2
    
    async def decide(self, intent: Intent) -> Decision:
        """Make a decision on an intent."""
        with tracer.start_as_current_span("decide") as span:
            span.set_attribute("intent.type", intent.type)
            span.set_attribute("intent.resource", intent.resource)
            span.set_attribute("intent.action", intent.action)
            
            # Check replan limit
            replan_count = intent.meta.get("replan_count", 0)
            if replan_count >= self.REPLAN_LIMIT:
                return Decision(
                    action="deny",
                    reason="replan_limit_exceeded",
                    why=f"Replan limit of {self.REPLAN_LIMIT} exceeded",
                    evidence={"replan_count": replan_count}
                )
            
            # 1. Check incident suppressor
            if await self._check_incident_suppressor(intent):
                return Decision(
                    action="deny",
                    reason="incident_suppressor",
                    why="Intent type is suppressed due to active incident",
                    evidence={"suppressed_type": intent.type}
                )
            
            # 2. Check frequency caps
            freq_check = await self._check_frequency_caps(intent)
            if not freq_check["allowed"]:
                return Decision(
                    action="deny",
                    reason="frequency_cap",
                    why=f"Frequency cap exceeded for {intent.type}",
                    evidence=freq_check["evidence"]
                )
            
            # 3. Handle calendar booking specifically
            if intent.type == "calendar.book":
                return await self._handle_calendar_booking(intent)
            
            # 4. Handle generic writes
            if intent.scope == "write":
                return await self._handle_generic_write(intent)
            
            # 5. Default accept for reads
            return Decision(
                action="accept",
                reason="read_operation",
                why="Read operation allowed",
                ttl_s=intent.ttl_s
            )
    
    async def _check_incident_suppressor(self, intent: Intent) -> bool:
        """Check if intent type is suppressed due to incidents."""
        return await self.policy_manager.is_suppressed(intent.type)
    
    async def _check_frequency_caps(self, intent: Intent) -> Dict[str, Any]:
        """Check frequency caps for the intent type."""
        cap_config = await self.policy_manager.get_frequency_cap(intent.type)
        if not cap_config:
            return {"allowed": True, "evidence": {}}
        
        window_hours = cap_config.get("window_hours", 24)
        since = datetime.utcnow() - timedelta(hours=window_hours)
        
        # Check recent activity for this resource
        recent_count = await self.store.get_recent_activity_count(
            intent.type, intent.resource, since
        )
        
        max_count = cap_config.get("max_count", 1)
        allowed = recent_count < max_count
        
        return {
            "allowed": allowed,
            "evidence": {
                "recent_count": recent_count,
                "max_count": max_count,
                "window_hours": window_hours,
                "since": since.isoformat()
            }
        }
    
    async def _handle_calendar_booking(self, intent: Intent) -> Decision:
        """Handle calendar booking with hold mechanism."""
        # Try to get a hold on the resource
        hold_response = await self.hold_manager.request_hold(
            resource=intent.resource,
            ttl_s=intent.ttl_s,
            author=intent.author
        )
        
        if hold_response.ok:
            return Decision(
                action="hold",
                reason="calendar_hold_granted",
                why="Hold granted for calendar booking",
                hold_id=hold_response.hold_id,
                ttl_s=intent.ttl_s
            )
        else:
            # Generate suggestions for replan
            suggestions = await self._generate_booking_suggestions(intent.resource)
            return Decision(
                action="replan",
                reason="calendar_conflict",
                why="Calendar slot is already booked",
                suggested=suggestions,
                evidence={"hold_denied": True}
            )
    
    async def _handle_generic_write(self, intent: Intent) -> Decision:
        """Handle generic write operations with locks."""
        # Check if resource is already locked
        is_locked = await self.lock_manager.is_locked(intent.resource)
        
        if is_locked:
            return Decision(
                action="replan",
                reason="resource_locked",
                why="Resource is currently locked by another operation",
                evidence={"locked": True}
            )
        
        # Try to acquire lock
        lock_acquired = await self.lock_manager.acquire_lock(
            intent.resource, intent.ttl_s
        )
        
        if lock_acquired:
            return Decision(
                action="accept",
                reason="lock_acquired",
                why="Lock acquired, operation allowed",
                ttl_s=intent.ttl_s
            )
        else:
            return Decision(
                action="replan",
                reason="lock_failed",
                why="Failed to acquire lock on resource",
                evidence={"lock_failed": True}
            )
    
    async def _generate_booking_suggestions(self, resource: str) -> List[str]:
        """Generate booking suggestions for calendar conflicts."""
        # Parse resource to extract time info
        # Format: "calendar:doctor:lee@2025-09-01T10:00:00-04:00"
        try:
            parts = resource.split("@")
            if len(parts) == 2:
                base = parts[0]
                time_str = parts[1]
                
                # Generate suggestions at 30, 60, 90 minute offsets
                suggestions = []
                for offset in [30, 60, 90]:
                    # This is a simplified suggestion generator
                    # In production, you'd integrate with actual calendar API
                    suggestion = f"{base}@{time_str}+{offset}m"
                    suggestions.append(suggestion)
                
                return suggestions
        except Exception:
            pass
        
        return []
    
    async def record_decision(self, intent: Intent, decision: Decision) -> None:
        """Record the decision for audit purposes."""
        await self.store.record_decision(intent, decision)
