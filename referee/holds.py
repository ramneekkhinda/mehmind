"""Hold manager for resource holds with fairness and TTL."""

import os
import uuid
import asyncio
from typing import Optional, List
from datetime import datetime, timedelta

import redis.asyncio as redis
from opentelemetry import trace

from .schemas import HoldResponse

tracer = trace.get_tracer(__name__)


class HoldManager:
    """Redis-based hold manager for resource holds."""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[redis.Redis] = None
        self.default_ttl = 120  # 2 minutes default TTL
    
    async def connect(self):
        """Connect to Redis."""
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        await self.redis.ping()
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
    
    async def request_hold(
        self, 
        resource: str, 
        ttl_s: int, 
        author: str, 
        correlation: Optional[str] = None
    ) -> HoldResponse:
        """Request a hold on a resource."""
        with tracer.start_as_current_span("request_hold") as span:
            span.set_attribute("resource", resource)
            span.set_attribute("ttl_s", ttl_s)
            span.set_attribute("author", author)
            
            if not self.redis:
                raise RuntimeError("Hold manager not connected")
            
            hold_id = f"h_{uuid.uuid4().hex[:12]}"
            lease_key = f"lease:{resource}"
            queue_key = f"q:{resource}"
            
            # Check if resource is already held
            existing_hold = await self.redis.hgetall(lease_key)
            
            if existing_hold:
                # Resource is already held, add to queue
                await self.redis.lpush(queue_key, f"{hold_id}:{author}:{correlation or ''}")
                await self.redis.expire(queue_key, ttl_s * 2)  # Queue TTL
                
                # Generate suggestions
                suggestions = await self._generate_suggestions(resource)
                
                return HoldResponse(
                    ok=False,
                    hold_id=None,
                    suggested=suggestions,
                    reason="resource_already_held"
                )
            
            # Try to acquire hold
            hold_data = {
                "hold_id": hold_id,
                "author": author,
                "correlation": correlation or "",
                "created_at": datetime.utcnow().isoformat(),
                "ttl_s": str(ttl_s)
            }
            
            # Use HSET with PEXPIRE for atomic operation
            pipe = self.redis.pipeline()
            pipe.hset(lease_key, mapping=hold_data)
            pipe.pexpire(lease_key, ttl_s * 1000)  # Convert to milliseconds
            results = await pipe.execute()
            
            if results[0] > 0:  # HSET succeeded
                return HoldResponse(
                    ok=True,
                    hold_id=hold_id,
                    suggested=None,
                    reason=None
                )
            else:
                # Race condition - someone else got the hold
                suggestions = await self._generate_suggestions(resource)
                return HoldResponse(
                    ok=False,
                    hold_id=None,
                    suggested=suggestions,
                    reason="race_condition"
                )
    
    async def confirm_hold(self, hold_id: str) -> bool:
        """Confirm a hold (mark as confirmed)."""
        with tracer.start_as_current_span("confirm_hold") as span:
            span.set_attribute("hold_id", hold_id)
            
            if not self.redis:
                raise RuntimeError("Hold manager not connected")
            
            # Find the lease that contains this hold_id
            lease_keys = await self.redis.keys("lease:*")
            
            for lease_key in lease_keys:
                hold_data = await self.redis.hgetall(lease_key)
                if hold_data.get("hold_id") == hold_id:
                    # Mark as confirmed
                    await self.redis.hset(lease_key, "confirmed", "true")
                    span.set_attribute("hold.confirmed", True)
                    return True
            
            span.set_attribute("hold.confirmed", False)
            return False
    
    async def release_hold(self, hold_id: str) -> bool:
        """Release a hold and potentially grant to next in queue."""
        with tracer.start_as_current_span("release_hold") as span:
            span.set_attribute("hold_id", hold_id)
            
            if not self.redis:
                raise RuntimeError("Hold manager not connected")
            
            # Find the lease that contains this hold_id
            lease_keys = await self.redis.keys("lease:*")
            
            for lease_key in lease_keys:
                hold_data = await self.redis.hgetall(lease_key)
                if hold_data.get("hold_id") == hold_id:
                    resource = lease_key.replace("lease:", "")
                    queue_key = f"q:{resource}"
                    
                    # Delete the lease
                    await self.redis.delete(lease_key)
                    
                    # Check if there's someone waiting in the queue
                    next_requester = await self.redis.rpop(queue_key)
                    if next_requester:
                        # Parse next requester
                        parts = next_requester.split(":")
                        if len(parts) >= 2:
                            next_hold_id = parts[0]
                            next_author = parts[1]
                            next_correlation = parts[2] if len(parts) > 2 else ""
                            
                            # Grant hold to next requester
                            ttl_s = int(hold_data.get("ttl_s", self.default_ttl))
                            new_hold_data = {
                                "hold_id": next_hold_id,
                                "author": next_author,
                                "correlation": next_correlation,
                                "created_at": datetime.utcnow().isoformat(),
                                "ttl_s": str(ttl_s)
                            }
                            
                            pipe = self.redis.pipeline()
                            pipe.hset(lease_key, mapping=new_hold_data)
                            pipe.pexpire(lease_key, ttl_s * 1000)
                            await pipe.execute()
                    
                    span.set_attribute("hold.released", True)
                    return True
            
            span.set_attribute("hold.released", False)
            return False
    
    async def get_hold_info(self, hold_id: str) -> Optional[dict]:
        """Get information about a hold."""
        with tracer.start_as_current_span("get_hold_info") as span:
            span.set_attribute("hold_id", hold_id)
            
            if not self.redis:
                raise RuntimeError("Hold manager not connected")
            
            # Find the lease that contains this hold_id
            lease_keys = await self.redis.keys("lease:*")
            
            for lease_key in lease_keys:
                hold_data = await self.redis.hgetall(lease_key)
                if hold_data.get("hold_id") == hold_id:
                    resource = lease_key.replace("lease:", "")
                    ttl = await self.redis.pttl(lease_key)
                    
                    info = {
                        "hold_id": hold_id,
                        "resource": resource,
                        "author": hold_data.get("author"),
                        "correlation": hold_data.get("correlation"),
                        "created_at": hold_data.get("created_at"),
                        "ttl_s": int(hold_data.get("ttl_s", 0)),
                        "ttl_ms": ttl,
                        "confirmed": hold_data.get("confirmed", "false") == "true"
                    }
                    
                    span.set_attribute("hold.info", str(info))
                    return info
            
            return None
    
    async def _generate_suggestions(self, resource: str) -> List[str]:
        """Generate suggestions for resource conflicts."""
        # Parse resource to extract time info for calendar resources
        # Format: "calendar:doctor:lee@2025-09-01T10:00:00-04:00"
        try:
            if resource.startswith("calendar:"):
                parts = resource.split("@")
                if len(parts) == 2:
                    base = parts[0]
                    time_str = parts[1]
                    
                    # Generate suggestions at 30, 60, 90 minute offsets
                    suggestions = []
                    for offset in [30, 60, 90]:
                        suggestion = f"{base}@{time_str}+{offset}m"
                        suggestions.append(suggestion)
                    
                    return suggestions
        except Exception:
            pass
        
        return []
    
    async def cleanup_expired_holds(self) -> int:
        """Clean up expired holds and process queues."""
        if not self.redis:
            return 0
        
        cleaned_count = 0
        
        # Get all lease keys
        lease_keys = await self.redis.keys("lease:*")
        
        for lease_key in lease_keys:
            # Check if lease has expired
            ttl = await self.redis.pttl(lease_key)
            if ttl <= 0:
                resource = lease_key.replace("lease:", "")
                queue_key = f"q:{resource}"
                
                # Delete expired lease
                await self.redis.delete(lease_key)
                cleaned_count += 1
                
                # Process queue for this resource
                next_requester = await self.redis.rpop(queue_key)
                if next_requester:
                    # Grant hold to next requester
                    parts = next_requester.split(":")
                    if len(parts) >= 2:
                        next_hold_id = parts[0]
                        next_author = parts[1]
                        next_correlation = parts[2] if len(parts) > 2 else ""
                        
                        new_hold_data = {
                            "hold_id": next_hold_id,
                            "author": next_author,
                            "correlation": next_correlation,
                            "created_at": datetime.utcnow().isoformat(),
                            "ttl_s": str(self.default_ttl)
                        }
                        
                        pipe = self.redis.pipeline()
                        pipe.hset(lease_key, mapping=new_hold_data)
                        pipe.pexpire(lease_key, self.default_ttl * 1000)
                        await pipe.execute()
        
        return cleaned_count
