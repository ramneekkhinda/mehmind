"""Policy manager for MeshMind referee service."""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class PolicyManager:
    """Policy manager for loading and managing YAML-based policies."""
    
    def __init__(self):
        self.policy_file = os.getenv("MESHMIND_POLICY_FILE", "policy.yaml")
        self.policy: Dict[str, Any] = {}
        self.suppressed_types: set = set()
    
    async def load_policy(self) -> None:
        """Load policy from YAML file."""
        with tracer.start_as_current_span("load_policy") as span:
            span.set_attribute("policy.file", self.policy_file)
            
            try:
                policy_path = Path(self.policy_file)
                if policy_path.exists():
                    with open(policy_path, 'r') as f:
                        self.policy = yaml.safe_load(f) or {}
                else:
                    # Load default policy
                    self.policy = self._get_default_policy()
                
                # Update suppressed types
                self._update_suppressed_types()
                
                span.set_attribute("policy.loaded", True)
                span.set_attribute("policy.suppressed_count", len(self.suppressed_types))
                
            except Exception as e:
                span.set_attribute("policy.error", str(e))
                # Fall back to default policy
                self.policy = self._get_default_policy()
                self._update_suppressed_types()
    
    def _get_default_policy(self) -> Dict[str, Any]:
        """Get default policy configuration."""
        return {
            "frequency_caps": {
                "contact.email": {
                    "window_hours": 48,
                    "max_count": 1
                },
                "contact.sms": {
                    "window_hours": 24,
                    "max_count": 2
                },
                "calendar.book": {
                    "window_hours": 1,
                    "max_count": 1
                }
            },
            "incidents": {
                "suppress_outreach": False,
                "suppressed_types": []
            },
            "approvals": {
                "booking": {
                    "require_if": [
                        "conflict_override"
                    ]
                },
                "high_value": {
                    "require_if": [
                        "amount_gt_1000"
                    ]
                }
            },
            "limits": {
                "replan_limit": 2,
                "max_hold_ttl": 3600,
                "default_hold_ttl": 120
            }
        }
    
    def _update_suppressed_types(self) -> None:
        """Update the set of suppressed intent types."""
        self.suppressed_types.clear()
        
        incidents = self.policy.get("incidents", {})
        if incidents.get("suppress_outreach", False):
            # Suppress all outreach-related types
            self.suppressed_types.update([
                "contact.email",
                "contact.sms",
                "contact.call"
            ])
        
        # Add explicitly suppressed types
        suppressed_types = incidents.get("suppressed_types", [])
        self.suppressed_types.update(suppressed_types)
    
    async def is_suppressed(self, intent_type: str) -> bool:
        """Check if an intent type is suppressed."""
        return intent_type in self.suppressed_types
    
    async def get_frequency_cap(self, intent_type: str) -> Optional[Dict[str, Any]]:
        """Get frequency cap configuration for an intent type."""
        frequency_caps = self.policy.get("frequency_caps", {})
        return frequency_caps.get(intent_type)
    
    async def get_approval_requirements(self, intent_type: str) -> Optional[Dict[str, Any]]:
        """Get approval requirements for an intent type."""
        approvals = self.policy.get("approvals", {})
        return approvals.get(intent_type)
    
    async def get_limits(self) -> Dict[str, Any]:
        """Get general limits configuration."""
        return self.policy.get("limits", {})
    
    async def reload_policy(self) -> None:
        """Reload policy from file."""
        await self.load_policy()
    
    async def update_policy(self, new_policy: Dict[str, Any]) -> None:
        """Update policy in memory."""
        with tracer.start_as_current_span("update_policy") as span:
            self.policy = new_policy
            self._update_suppressed_types()
            
            span.set_attribute("policy.updated", True)
            span.set_attribute("policy.suppressed_count", len(self.suppressed_types))
    
    async def save_policy(self) -> bool:
        """Save current policy to file."""
        with tracer.start_as_current_span("save_policy") as span:
            try:
                policy_path = Path(self.policy_file)
                with open(policy_path, 'w') as f:
                    yaml.dump(self.policy, f, default_flow_style=False)
                
                span.set_attribute("policy.saved", True)
                return True
            except Exception as e:
                span.set_attribute("policy.save_error", str(e))
                return False
    
    def get_policy_summary(self) -> Dict[str, Any]:
        """Get a summary of the current policy."""
        return {
            "frequency_caps": list(self.policy.get("frequency_caps", {}).keys()),
            "suppressed_types": list(self.suppressed_types),
            "approval_types": list(self.policy.get("approvals", {}).keys()),
            "limits": self.policy.get("limits", {})
        }
