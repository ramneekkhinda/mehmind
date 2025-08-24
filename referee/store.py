"""PostgreSQL store for MeshMind referee service."""

import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

import asyncpg
from opentelemetry import trace

from .schemas import Intent, Decision

tracer = trace.get_tracer(__name__)


class Store:
    """PostgreSQL store for audit trails and metrics."""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql://meshmind:meshmind@localhost/meshmind")
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Connect to PostgreSQL and create tables."""
        self.pool = await asyncpg.create_pool(self.database_url)
        await self._create_tables()
    
    async def disconnect(self):
        """Disconnect from PostgreSQL."""
        if self.pool:
            await self.pool.close()
    
    async def _create_tables(self):
        """Create database tables if they don't exist."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    tags JSONB DEFAULT '{}'::jsonb
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    run_id UUID REFERENCES runs(id),
                    intent JSONB NOT NULL,
                    decision JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS holds (
                    hold_id TEXT PRIMARY KEY,
                    resource TEXT NOT NULL,
                    author TEXT NOT NULL,
                    ttl_s INTEGER NOT NULL,
                    state TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    budget_id TEXT PRIMARY KEY,
                    caps JSONB NOT NULL,
                    spent_usd NUMERIC(10,4) DEFAULT 0,
                    spent_tokens INTEGER DEFAULT 0,
                    rpm INTEGER NOT NULL,
                    state TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    run_id UUID REFERENCES runs(id),
                    event TEXT NOT NULL,
                    payload JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_run_id ON decisions(run_id);
                CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at);
                CREATE INDEX IF NOT EXISTS idx_holds_resource ON holds(resource);
                CREATE INDEX IF NOT EXISTS idx_holds_state ON holds(state);
                CREATE INDEX IF NOT EXISTS idx_budgets_state ON budgets(state);
                CREATE INDEX IF NOT EXISTS idx_audit_run_id ON audit(run_id);
                CREATE INDEX IF NOT EXISTS idx_audit_event ON audit(event);
            """)
    
    async def create_run(self, tags: Dict[str, Any] = None) -> str:
        """Create a new run and return its ID."""
        async with self.pool.acquire() as conn:
            run_id = await conn.fetchval(
                "INSERT INTO runs (tags) VALUES ($1) RETURNING id",
                tags or {}
            )
            return str(run_id)
    
    async def record_decision(self, intent: Intent, decision: Decision, run_id: Optional[str] = None) -> str:
        """Record a decision for audit purposes."""
        async with self.pool.acquire() as conn:
            decision_id = await conn.fetchval(
                """
                INSERT INTO decisions (run_id, intent, decision)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                run_id,
                intent.model_dump(),
                decision.model_dump()
            )
            return str(decision_id)
    
    async def record_hold(self, hold_id: str, resource: str, author: str, ttl_s: int) -> None:
        """Record a hold creation."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO holds (hold_id, resource, author, ttl_s, state)
                VALUES ($1, $2, $3, $4, 'pending')
                ON CONFLICT (hold_id) DO UPDATE SET
                    updated_at = NOW(),
                    state = 'pending'
                """,
                hold_id, resource, author, ttl_s
            )
    
    async def update_hold_state(self, hold_id: str, state: str) -> None:
        """Update hold state."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE holds SET state = $1, updated_at = NOW() WHERE hold_id = $2",
                state, hold_id
            )
    
    async def record_budget(self, budget_id: str, caps: Dict[str, Any], rpm: int) -> None:
        """Record a budget creation."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO budgets (budget_id, caps, rpm, state)
                VALUES ($1, $2, $3, 'active')
                ON CONFLICT (budget_id) DO UPDATE SET
                    updated_at = NOW(),
                    caps = $2,
                    rpm = $3
                """,
                budget_id, caps, rpm
            )
    
    async def update_budget_spending(self, budget_id: str, spent_usd: float, spent_tokens: int) -> None:
        """Update budget spending."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE budgets 
                SET spent_usd = spent_usd + $2, 
                    spent_tokens = spent_tokens + $3,
                    updated_at = NOW()
                WHERE budget_id = $1
                """,
                budget_id, spent_usd, spent_tokens
            )
    
    async def update_budget_state(self, budget_id: str, state: str) -> None:
        """Update budget state."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE budgets SET state = $1, updated_at = NOW() WHERE budget_id = $2",
                state, budget_id
            )
    
    async def record_audit_event(self, event: str, payload: Dict[str, Any] = None, run_id: Optional[str] = None) -> str:
        """Record an audit event."""
        async with self.pool.acquire() as conn:
            audit_id = await conn.fetchval(
                "INSERT INTO audit (run_id, event, payload) VALUES ($1, $2, $3) RETURNING id",
                run_id, event, payload or {}
            )
            return str(audit_id)
    
    async def get_recent_activity_count(self, intent_type: str, resource: str, since: datetime) -> int:
        """Get count of recent activity for frequency caps."""
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM decisions 
                WHERE intent->>'type' = $1 
                AND intent->>'resource' = $2 
                AND created_at >= $3
                """,
                intent_type, resource, since
            )
            return count or 0
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        async with self.pool.acquire() as conn:
            # Decision counts by action
            decision_counts = await conn.fetch(
                """
                SELECT decision->>'action' as action, COUNT(*) as count
                FROM decisions 
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                GROUP BY decision->>'action'
                """
            )
            
            # Active holds count
            active_holds = await conn.fetchval(
                "SELECT COUNT(*) FROM holds WHERE state = 'pending'"
            )
            
            # Active budgets count
            active_budgets = await conn.fetchval(
                "SELECT COUNT(*) FROM budgets WHERE state = 'active'"
            )
            
            # Total spending in last hour
            total_spending = await conn.fetchval(
                """
                SELECT COALESCE(SUM(spent_usd), 0) 
                FROM budgets 
                WHERE updated_at >= NOW() - INTERVAL '1 hour'
                """
            )
            
            # Recent decisions (last 10)
            recent_decisions = await conn.fetch(
                """
                SELECT intent->>'type' as type, decision->>'action' as action, created_at
                FROM decisions 
                ORDER BY created_at DESC 
                LIMIT 10
                """
            )
            
            return {
                "decision_counts": {row["action"]: row["count"] for row in decision_counts},
                "active_holds": active_holds or 0,
                "active_budgets": active_budgets or 0,
                "total_spending_last_hour": float(total_spending or 0),
                "recent_decisions": [
                    {
                        "type": row["type"],
                        "action": row["action"],
                        "created_at": row["created_at"].isoformat()
                    }
                    for row in recent_decisions
                ]
            }
    
    async def get_decision_history(self, resource: str, limit: int = 10) -> list:
        """Get decision history for a resource."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT intent, decision, created_at
                FROM decisions 
                WHERE intent->>'resource' = $1
                ORDER BY created_at DESC 
                LIMIT $2
                """,
                resource, limit
            )
            
            return [
                {
                    "intent": row["intent"],
                    "decision": row["decision"],
                    "created_at": row["created_at"].isoformat()
                }
                for row in rows
            ]
    
    async def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """Clean up old data."""
        async with self.pool.acquire() as conn:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            # Clean up old decisions
            decisions_deleted = await conn.execute(
                "DELETE FROM decisions WHERE created_at < $1",
                cutoff
            )
            
            # Clean up old audit events
            audit_deleted = await conn.execute(
                "DELETE FROM audit WHERE created_at < $1",
                cutoff
            )
            
            # Clean up old runs
            runs_deleted = await conn.execute(
                "DELETE FROM runs WHERE created_at < $1",
                cutoff
            )
            
            return {
                "decisions_deleted": int(decisions_deleted.split()[-1]),
                "audit_deleted": int(audit_deleted.split()[-1]),
                "runs_deleted": int(runs_deleted.split()[-1])
            }
