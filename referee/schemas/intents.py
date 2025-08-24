"""Intent and Decision schemas for MeshMind Referee Service."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Intent(BaseModel):
    """Intent schema for preflight requests."""
    
    type: str = Field(..., description="Intent type (e.g., 'contact.email', 'calendar.book')")
    resource: str = Field(..., description="Resource identifier (e.g., 'contact:42/email')")
    action: str = Field(..., description="Action to perform (e.g., 'send', 'book')")
    author: str = Field(..., description="Author/agent identifier")
    scope: Literal["read", "write"] = Field(..., description="Access scope")
    ttl_s: int = Field(..., ge=1, le=3600, description="Time-to-live in seconds")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Decision(BaseModel):
    """Decision response from referee service."""
    
    action: Literal["accept", "replan", "hold", "deny"] = Field(..., description="Decision action")
    reason: str = Field(..., description="Reason for decision")
    why: str = Field(..., description="Human-readable explanation")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Supporting evidence")
    hold_id: Optional[str] = Field(None, description="Hold ID if action is 'hold'")
    ttl_s: Optional[int] = Field(None, description="TTL for hold/decision")
    suggested: Optional[List[str]] = Field(None, description="Suggested alternatives")


class HoldRequest(BaseModel):
    """Request to hold a resource."""
    
    resource: str = Field(..., description="Resource to hold")
    ttl_s: int = Field(..., ge=1, le=3600, description="Hold duration in seconds")
    author: str = Field(..., description="Author requesting hold")
    correlation: Optional[str] = Field(None, description="Correlation ID")


class HoldResponse(BaseModel):
    """Response to hold request."""
    
    ok: bool = Field(..., description="Whether hold was granted")
    hold_id: Optional[str] = Field(None, description="Hold ID if granted")
    suggested: Optional[List[str]] = Field(None, description="Suggested alternatives if denied")
    reason: Optional[str] = Field(None, description="Reason if denied")
