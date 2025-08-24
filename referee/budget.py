"""Budget manager for cost control and rate limiting."""

import os
import uuid
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import redis.asyncio as redis
from opentelemetry import trace

from .schemas import BudgetResponse

tracer = trace.get_tracer(__name__)


class BudgetManager:
    """Redis-based budget manager for cost control."""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis."""
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis.ping()
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
    
    async def start_budget(
        self, 
        usd_cap: float, 
        rpm: int, 
        tags: Dict[str, Any]
    ) -> BudgetResponse:
        """Start a new budget session."""
        with tracer.start_as_current_span("start_budget") as span:
            span.set_attribute("usd_cap", usd_cap)
            span.set_attribute("rpm", rpm)
            
            if not self.redis:
                raise RuntimeError("Budget manager not connected")
            
            budget_id = f"b_{uuid.uuid4().hex[:12]}"
            
            # Create budget data
            budget_data = {
                "usd_cap": str(usd_cap),
                "rpm": str(rpm),
                "spent_usd": "0.0",
                "spent_tokens": "0",
                "created_at": datetime.utcnow().isoformat(),
                "state": "active"
            }
            
            # Add tags
            for key, value in tags.items():
                budget_data[f"tag_{key}"] = str(value)
            
            # Store budget in Redis
            budget_key = f"budget:{budget_id}"
            await self.redis.hset(budget_key, mapping=budget_data)
            await self.redis.expire(budget_key, 3600)  # 1 hour TTL
            
            # Initialize rate limiting
            rpm_key = f"rpm:{budget_id}"
            await self.redis.expire(rpm_key, 60)  # 1 minute window
            
            span.set_attribute("budget.id", budget_id)
            
            return BudgetResponse(
                budget_id=budget_id,
                remaining_usd=usd_cap,
                remaining_tokens=None,
                ok=True,
                reason=None
            )
    
    async def consume_budget(
        self, 
        budget_id: str, 
        tokens: int, 
        usd: float
    ) -> BudgetResponse:
        """Consume from a budget."""
        with tracer.start_as_current_span("consume_budget") as span:
            span.set_attribute("budget_id", budget_id)
            span.set_attribute("tokens", tokens)
            span.set_attribute("usd", usd)
            
            if not self.redis:
                raise RuntimeError("Budget manager not connected")
            
            budget_key = f"budget:{budget_id}"
            rpm_key = f"rpm:{budget_id}"
            
            # Get current budget data
            budget_data = await self.redis.hgetall(budget_key)
            if not budget_data:
                return BudgetResponse(
                    budget_id=budget_id,
                    remaining_usd=0.0,
                    remaining_tokens=0,
                    ok=False,
                    reason="budget_not_found"
                )
            
            # Check if budget is still active
            if budget_data.get("state") != "active":
                return BudgetResponse(
                    budget_id=budget_id,
                    remaining_usd=0.0,
                    remaining_tokens=0,
                    ok=False,
                    reason="budget_inactive"
                )
            
            # Check rate limiting
            current_rpm = await self.redis.incr(rpm_key)
            max_rpm = int(budget_data.get("rpm", 0))
            
            if current_rpm > max_rpm:
                return BudgetResponse(
                    budget_id=budget_id,
                    remaining_usd=float(budget_data.get("spent_usd", 0)),
                    remaining_tokens=int(budget_data.get("spent_tokens", 0)),
                    ok=False,
                    reason="rate_limit_exceeded"
                )
            
            # Calculate new totals
            current_spent_usd = float(budget_data.get("spent_usd", 0))
            current_spent_tokens = int(budget_data.get("spent_tokens", 0))
            usd_cap = float(budget_data.get("usd_cap", 0))
            
            new_spent_usd = current_spent_usd + usd
            new_spent_tokens = current_spent_tokens + tokens
            
            # Check if we would exceed the cap
            if new_spent_usd > usd_cap:
                return BudgetResponse(
                    budget_id=budget_id,
                    remaining_usd=usd_cap - current_spent_usd,
                    remaining_tokens=0,
                    ok=False,
                    reason="budget_exceeded"
                )
            
            # Update budget
            await self.redis.hset(budget_key, mapping={
                "spent_usd": str(new_spent_usd),
                "spent_tokens": str(new_spent_tokens),
                "last_consumed": datetime.utcnow().isoformat()
            })
            
            remaining_usd = usd_cap - new_spent_usd
            
            span.set_attribute("budget.remaining_usd", remaining_usd)
            span.set_attribute("budget.consumed", True)
            
            return BudgetResponse(
                budget_id=budget_id,
                remaining_usd=remaining_usd,
                remaining_tokens=new_spent_tokens,
                ok=True,
                reason=None
            )
    
    async def stop_budget(self, budget_id: str) -> bool:
        """Stop a budget session."""
        with tracer.start_as_current_span("stop_budget") as span:
            span.set_attribute("budget_id", budget_id)
            
            if not self.redis:
                raise RuntimeError("Budget manager not connected")
            
            budget_key = f"budget:{budget_id}"
            rpm_key = f"rpm:{budget_id}"
            
            # Mark budget as stopped
            await self.redis.hset(budget_key, "state", "stopped")
            await self.redis.hset(budget_key, "stopped_at", datetime.utcnow().isoformat())
            
            # Clean up rate limiting
            await self.redis.delete(rpm_key)
            
            span.set_attribute("budget.stopped", True)
            return True
    
    async def get_budget_info(self, budget_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a budget."""
        with tracer.start_as_current_span("get_budget_info") as span:
            span.set_attribute("budget_id", budget_id)
            
            if not self.redis:
                raise RuntimeError("Budget manager not connected")
            
            budget_key = f"budget:{budget_id}"
            budget_data = await self.redis.hgetall(budget_key)
            
            if not budget_data:
                return None
            
            # Calculate remaining budget
            usd_cap = float(budget_data.get("usd_cap", 0))
            spent_usd = float(budget_data.get("spent_usd", 0))
            remaining_usd = usd_cap - spent_usd
            
            info = {
                "budget_id": budget_id,
                "usd_cap": usd_cap,
                "spent_usd": spent_usd,
                "remaining_usd": remaining_usd,
                "spent_tokens": int(budget_data.get("spent_tokens", 0)),
                "rpm": int(budget_data.get("rpm", 0)),
                "state": budget_data.get("state"),
                "created_at": budget_data.get("created_at"),
                "last_consumed": budget_data.get("last_consumed"),
                "stopped_at": budget_data.get("stopped_at")
            }
            
            # Add tags
            tags = {}
            for key, value in budget_data.items():
                if key.startswith("tag_"):
                    tag_key = key[4:]  # Remove "tag_" prefix
                    tags[tag_key] = value
            info["tags"] = tags
            
            span.set_attribute("budget.info", str(info))
            return info
    
    async def cleanup_expired_budgets(self) -> int:
        """Clean up expired budgets."""
        if not self.redis:
            return 0
        
        cleaned_count = 0
        
        # Get all budget keys
        budget_keys = await self.redis.keys("budget:*")
        
        for budget_key in budget_keys:
            # Check if budget has expired (TTL)
            ttl = await self.redis.ttl(budget_key)
            if ttl <= 0:
                budget_id = budget_key.replace("budget:", "")
                rpm_key = f"rpm:{budget_id}"
                
                # Clean up budget and rate limiting
                await self.redis.delete(budget_key)
                await self.redis.delete(rpm_key)
                cleaned_count += 1
        
        return cleaned_count
