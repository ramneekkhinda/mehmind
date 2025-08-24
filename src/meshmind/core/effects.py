"""
MeshMind Idempotent Effects Module

Idempotent HTTP and email operations with conflict detection.
"""

import httpx
from typing import Dict, Any, Optional

from ..utils.errors import IdempotencyConflictError
from ..utils.logging import get_logger, log_effect_operation

logger = get_logger(__name__)


async def http_post(
    url: str,
    data: Dict[str, Any],
    idempotency_key: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Make an idempotent HTTP POST request.
    
    Args:
        url: Target URL for the POST request
        data: Request payload
        idempotency_key: Unique key for idempotency
        headers: Optional additional headers
        timeout: Request timeout in seconds
        
    Returns:
        Response data from the HTTP request
        
    Raises:
        IdempotencyConflictError: When idempotency key conflicts
    """
    # Prepare headers with idempotency key
    request_headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotency_key,
        **(headers or {})
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json=data,
                headers=request_headers
            )
            
            # Check for idempotency conflicts
            if response.status_code == 409:
                log_effect_operation(
                    logger=logger,
                    effect_type="http_post",
                    resource=url,
                    idempotency_key=idempotency_key,
                    success=False
                )
                
                raise IdempotencyConflictError(
                    message=f"HTTP POST already executed with idempotency key: {idempotency_key}",
                    idempotency_key=idempotency_key,
                    resource_type="http_post"
                )
            
            response.raise_for_status()
            
            result = response.json()
            
            log_effect_operation(
                logger=logger,
                effect_type="http_post",
                resource=url,
                idempotency_key=idempotency_key,
                success=True,
                additional_data={
                    "status_code": response.status_code,
                    "response_size": len(response.content)
                }
            )
            
            return {
                "success": True,
                "status_code": response.status_code,
                "data": result,
                "idempotent": True
            }
            
    except httpx.RequestError as e:
        log_effect_operation(
            logger=logger,
            effect_type="http_post",
            resource=url,
            idempotency_key=idempotency_key,
            success=False,
            additional_data={"error": str(e)}
        )
        raise Exception(f"HTTP POST request failed: {e}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            raise IdempotencyConflictError(
                message=f"HTTP POST already executed with idempotency key: {idempotency_key}",
                idempotency_key=idempotency_key,
                resource_type="http_post"
            )
        else:
            log_effect_operation(
                logger=logger,
                effect_type="http_post",
                resource=url,
                idempotency_key=idempotency_key,
                success=False,
                additional_data={
                    "status_code": e.response.status_code,
                    "error": e.response.text
                }
            )
            raise Exception(f"HTTP POST error {e.response.status_code}: {e.response.text}")


async def email_send(
    contact_id: int,
    body: str,
    idempotency_key: str,
    subject: Optional[str] = None,
    from_email: Optional[str] = None,
    template: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send an idempotent email.
    
    Args:
        contact_id: Contact ID to send email to
        body: Email body content
        idempotency_key: Unique idempotency key
        subject: Email subject
        from_email: From email address
        template: Email template name
        metadata: Additional metadata
    
    Returns:
        Email send result
        
    Raises:
        IdempotencyConflictError: If idempotency key conflicts
    """
    # Simulate email service call
    # In a real implementation, this would call an actual email service
    
    try:
        # Simulate email service processing
        await asyncio.sleep(0.1)
        
        # Check for idempotency conflicts (simulated)
        # In real implementation, this would check against email service
        if idempotency_key.startswith("conflict_"):
            log_effect_operation(
                logger=logger,
                effect_type="email_send",
                resource=f"contact:{contact_id}",
                idempotency_key=idempotency_key,
                success=False
            )
            
            raise IdempotencyConflictError(
                message=f"Email already sent with idempotency key: {idempotency_key}",
                idempotency_key=idempotency_key,
                resource_type="email"
            )
        
        # Simulate successful email send
        email_id = f"email_{idempotency_key[:8]}"
        
        log_effect_operation(
            logger=logger,
            effect_type="email_send",
            resource=f"contact:{contact_id}",
            idempotency_key=idempotency_key,
            success=True,
            additional_data={
                "email_id": email_id,
                "subject": subject,
                "template": template
            }
        )
        
        return {
            "success": True,
            "email_id": email_id,
            "contact_id": contact_id,
            "idempotent": True,
            "subject": subject,
            "template": template
        }
        
    except Exception as e:
        log_effect_operation(
            logger=logger,
            effect_type="email_send",
            resource=f"contact:{contact_id}",
            idempotency_key=idempotency_key,
            success=False,
            additional_data={"error": str(e)}
        )
        raise


# Import asyncio for the async sleep
import asyncio
