"""
MeshMind Intent Preflight Module

Core functionality for intent preflight operations with the referee service.
"""

import time
from typing import Any, Dict, Optional

import httpx

from ..utils.config import MeshMindConfig
from ..utils.errors import PolicyDeniedError, RefereeConnectionError
from ..utils.logging import get_logger, log_intent_preflight

logger = get_logger(__name__)


class IntentsClient:
    """Client for intent preflight operations."""

    def __init__(self, config: Optional[MeshMindConfig] = None):
        """
        Initialize the intents client.

        Args:
            config: MeshMind configuration, defaults to environment-based config
        """
        self.config = config or MeshMindConfig.from_env()
        self._session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure HTTP session is initialized."""
        if self._session is None:
            limits = httpx.Limits(
                max_connections=self.config.connection_pool_size,
                max_keepalive_connections=self.config.connection_pool_size,
            )

            self._session = httpx.AsyncClient(
                timeout=self.config.timeout,
                limits=limits,
                verify=self.config.enable_ssl_verification,
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.aclose()
            self._session = None

    async def preflight(
        self, intent_type: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Preflight an intent with the referee service.

        Args:
            intent_type: Type of intent (e.g., "contact.email", "calendar.book")
            payload: Intent payload with resource, action, author, etc.

        Returns:
            Decision from referee service

        Raises:
            PolicyDeniedError: When intent is denied by policy
            RefereeConnectionError: When unable to connect to referee service
        """
        await self._ensure_session()

        start_time = time.time()

        # Prepare intent data
        intent_data = {
            "type": intent_type,
            "resource": payload["resource"],
            "action": payload.get("action", "execute"),
            "author": payload["author"],
            "scope": payload.get("scope", "write"),
            "ttl_s": payload.get("ttl_s", 90),
            "meta": payload.get("meta", {}),
        }

        # Prepare headers
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        try:
            response = await self._session.post(
                f"{self.config.base_url}/v1/intents", json=intent_data, headers=headers
            )

            processing_time_ms = (time.time() - start_time) * 1000

            # Handle different response status codes
            if response.status_code == 200:
                decision = response.json()

                # Log the preflight operation
                log_intent_preflight(
                    logger=logger,
                    intent_type=intent_type,
                    resource=payload["resource"],
                    decision=decision.get("action", "unknown"),
                    processing_time_ms=processing_time_ms,
                    additional_data={
                        "reason": decision.get("reason"),
                        "ttl_s": decision.get("ttl_s"),
                    },
                )

                # Check if decision indicates denial
                if decision["action"] == "deny":
                    raise PolicyDeniedError(
                        message=f"Intent denied: {decision.get('reason', 'unknown')}",
                        intent_type=intent_type,
                        resource=payload["resource"],
                        reason=decision.get("reason"),
                        details=decision,
                    )

                return decision

            elif response.status_code == 400:
                error_data = response.json()
                raise PolicyDeniedError(
                    message=f"Invalid intent: {error_data.get('detail', 'Bad request')}",
                    intent_type=intent_type,
                    resource=payload.get("resource"),
                    details=error_data,
                )

            elif response.status_code == 409:
                error_data = response.json()
                raise PolicyDeniedError(
                    message=f"Resource conflict: {error_data.get('detail', 'Conflict')}",
                    intent_type=intent_type,
                    resource=payload.get("resource"),
                    reason="resource_conflict",
                    details=error_data,
                )

            else:
                raise RefereeConnectionError(
                    message=f"Referee service error: {response.status_code} - {response.text}",
                    base_url=self.config.base_url,
                    details={
                        "status_code": response.status_code,
                        "response": response.text,
                    },
                )

        except httpx.RequestError as e:
            processing_time_ms = (time.time() - start_time) * 1000

            logger.warning(
                "Intent preflight request failed",
                extra={
                    "structured_data": {
                        "operation": "intent_preflight",
                        "intent_type": intent_type,
                        "resource": payload.get("resource"),
                        "error": str(e),
                        "processing_time_ms": processing_time_ms,
                    }
                },
            )

            if self.config.enable_graceful_degradation:
                logger.info("Graceful degradation: proceeding without preflight")
                return {"action": "accept", "reason": "graceful_degradation"}
            else:
                raise RefereeConnectionError(
                    message=f"Failed to connect to referee service: {e}",
                    base_url=self.config.base_url,
                    timeout=self.config.timeout,
                    details={"original_error": str(e)},
                )

    async def batch_preflight(self, intents: list) -> list:
        """
        Preflight multiple intents in batch.

        Args:
            intents: List of (intent_type, payload) tuples

        Returns:
            List of preflight results
        """
        results = []

        for intent_type, payload in intents:
            try:
                decision = await self.preflight(intent_type, payload)
                results.append(
                    {"success": True, "intent_type": intent_type, "decision": decision}
                )
            except Exception as e:
                results.append(
                    {
                        "success": False,
                        "intent_type": intent_type,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )

        return results


# Global client instance for convenience
_client: Optional[IntentsClient] = None


async def preflight_intent(
    intent_type: str, payload: Dict[str, Any], config: Optional[MeshMindConfig] = None
) -> Dict[str, Any]:
    """
    Preflight an intent with the referee service.

    This is a convenience function that uses a global client instance.
    For production use, consider creating your own IntentsClient instance.

    Args:
        intent_type: Type of intent (e.g., "contact.email", "calendar.book")
        payload: Intent payload with resource, action, author, etc.
        config: Optional configuration override

    Returns:
        Decision from referee service

    Raises:
        PolicyDeniedError: When intent is denied by policy
        RefereeConnectionError: When unable to connect to referee service
    """
    global _client

    if _client is None:
        _client = IntentsClient(config)

    return await _client.preflight(intent_type, payload)


async def close_intents_client() -> None:
    """Close the global intents client."""
    global _client
    if _client:
        await _client.close()
        _client = None
