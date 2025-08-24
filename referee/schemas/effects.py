"""Effects schemas for idempotent side-effects."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class EffectRequest(BaseModel):
    """Request to perform an idempotent effect."""
    
    effect_type: str = Field(..., description="Effect type (e.g., 'http_post', 'email_send')")
    idempotency_key: str = Field(..., description="Unique idempotency key")
    payload: Dict[str, Any] = Field(..., description="Effect payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EffectResponse(BaseModel):
    """Response from effect execution."""
    
    effect_id: str = Field(..., description="Effect execution ID")
    success: bool = Field(..., description="Whether effect succeeded")
    result: Optional[Dict[str, Any]] = Field(None, description="Effect result")
    error: Optional[str] = Field(None, description="Error message if failed")
    idempotent: bool = Field(..., description="Whether this was a duplicate request")
