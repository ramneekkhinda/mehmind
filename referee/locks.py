"""Redis-based lock manager for MeshMind."""

import os
import uuid
import asyncio
from typing import Optional
from datetime import datetime

import redis.asyncio as redis
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class LockManager:
    """Redis-based lock manager for resource locking."""
    
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
    
    async def acquire_lock(self, resource: str, ttl_s: int) -> bool:
        """Acquire a lock on a resource."""
        with tracer.start_as_current_span("acquire_lock") as span:
            span.set_attribute("resource", resource)
            span.set_attribute("ttl_s", ttl_s)
            
            if not self.redis:
                raise RuntimeError("Lock manager not connected")
            
            lock_key = f"lock:{resource}"
            lock_value = str(uuid.uuid4())
            
            # Use SET with NX (only if not exists) and EX (expiration)
            result = await self.redis.set(
                lock_key, 
                lock_value, 
                ex=ttl_s, 
                nx=True
            )
            
            acquired = result is True
            span.set_attribute("lock.acquired", acquired)
            
            if acquired:
                span.set_attribute("lock.value", lock_value)
            
            return acquired
    
    async def release_lock(self, resource: str, lock_value: str) -> bool:
        """Release a lock on a resource."""
        with tracer.start_as_current_span("release_lock") as span:
            span.set_attribute("resource", resource)
            span.set_attribute("lock.value", lock_value)
            
            if not self.redis:
                raise RuntimeError("Lock manager not connected")
            
            lock_key = f"lock:{resource}"
            
            # Use Lua script for atomic check-and-delete
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.redis.eval(lua_script, 1, lock_key, lock_value)
            released = result == 1
            
            span.set_attribute("lock.released", released)
            return released
    
    async def is_locked(self, resource: str) -> bool:
        """Check if a resource is currently locked."""
        with tracer.start_as_current_span("is_locked") as span:
            span.set_attribute("resource", resource)
            
            if not self.redis:
                raise RuntimeError("Lock manager not connected")
            
            lock_key = f"lock:{resource}"
            exists = await self.redis.exists(lock_key) == 1
            
            span.set_attribute("lock.exists", exists)
            return exists
    
    async def get_lock_info(self, resource: str) -> Optional[dict]:
        """Get information about a lock."""
        with tracer.start_as_current_span("get_lock_info") as span:
            span.set_attribute("resource", resource)
            
            if not self.redis:
                raise RuntimeError("Lock manager not connected")
            
            lock_key = f"lock:{resource}"
            
            # Get lock value and TTL
            lock_value = await self.redis.get(lock_key)
            if not lock_value:
                return None
            
            ttl = await self.redis.ttl(lock_key)
            
            info = {
                "resource": resource,
                "lock_value": lock_value,
                "ttl": ttl,
                "created_at": datetime.utcnow().isoformat()
            }
            
            span.set_attribute("lock.info", str(info))
            return info
    
    async def extend_lock(self, resource: str, lock_value: str, ttl_s: int) -> bool:
        """Extend the TTL of an existing lock."""
        with tracer.start_as_current_span("extend_lock") as span:
            span.set_attribute("resource", resource)
            span.set_attribute("lock.value", lock_value)
            span.set_attribute("ttl_s", ttl_s)
            
            if not self.redis:
                raise RuntimeError("Lock manager not connected")
            
            lock_key = f"lock:{resource}"
            
            # Use Lua script for atomic check-and-expire
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            
            result = await self.redis.eval(lua_script, 1, lock_key, lock_value, ttl_s)
            extended = result == 1
            
            span.set_attribute("lock.extended", extended)
            return extended
    
    async def cleanup_expired_locks(self) -> int:
        """Clean up expired locks (called by background task)."""
        # Redis automatically expires keys, so this is mainly for monitoring
        if not self.redis:
            return 0
        
        # Get all lock keys
        lock_keys = await self.redis.keys("lock:*")
        cleaned_count = 0
        
        for key in lock_keys:
            # Check if key still exists (not expired)
            if await self.redis.exists(key) == 0:
                cleaned_count += 1
        
        return cleaned_count
