"""Budget management schemas for MeshMind Referee Service."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class BudgetStart(BaseModel):
    """Request to start a budget session."""
    
    usd_cap: float = Field(..., gt=0, description="USD spending cap")
    rpm: int = Field(..., gt=0, description="Requests per minute limit")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Budget tags for tracking")


class BudgetConsume(BaseModel):
    """Request to consume from a budget."""
    
    budget_id: str = Field(..., description="Budget session ID")
    tokens: int = Field(..., ge=0, description="Tokens consumed")
    usd: float = Field(..., ge=0, description="USD spent")


class BudgetResponse(BaseModel):
    """Response from budget operations."""
    
    budget_id: str = Field(..., description="Budget session ID")
    remaining_usd: float = Field(..., description="Remaining USD budget")
    remaining_tokens: Optional[int] = Field(None, description="Remaining token budget")
    ok: bool = Field(..., description="Whether operation succeeded")
    reason: Optional[str] = Field(None, description="Reason if operation failed")
