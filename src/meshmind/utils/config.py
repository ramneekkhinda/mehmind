"""
MeshMind Configuration Management

Configuration classes and utilities for MeshMind client and services.
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MeshMindConfig:
    """Configuration for MeshMind client and services."""

    # Referee service configuration
    base_url: str = "http://localhost:8080"
    timeout: float = 10.0
    max_retries: int = 3
    retry_delay: float = 1.0

    # Graceful degradation settings
    enable_graceful_degradation: bool = True
    fallback_on_error: bool = True

    # Logging configuration
    log_level: str = "INFO"
    enable_structured_logging: bool = True

    # Performance settings
    connection_pool_size: int = 10
    keepalive_timeout: float = 30.0

    # Security settings
    api_key: Optional[str] = None
    enable_ssl_verification: bool = True

    # Additional metadata
    tags: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "MeshMindConfig":
        """Create configuration from environment variables."""
        return cls(
            base_url=os.getenv("MESHMIND_BASE_URL", "http://localhost:8080"),
            timeout=float(os.getenv("MESHMIND_TIMEOUT", "10.0")),
            max_retries=int(os.getenv("MESHMIND_MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("MESHMIND_RETRY_DELAY", "1.0")),
            enable_graceful_degradation=os.getenv(
                "MESHMIND_GRACEFUL_DEGRADATION", "true"
            ).lower()
            == "true",
            fallback_on_error=os.getenv("MESHMIND_FALLBACK_ON_ERROR", "true").lower()
            == "true",
            log_level=os.getenv("MESHMIND_LOG_LEVEL", "INFO"),
            enable_structured_logging=os.getenv(
                "MESHMIND_STRUCTURED_LOGGING", "true"
            ).lower()
            == "true",
            connection_pool_size=int(os.getenv("MESHMIND_POOL_SIZE", "10")),
            keepalive_timeout=float(os.getenv("MESHMIND_KEEPALIVE", "30.0")),
            api_key=os.getenv("MESHMIND_API_KEY"),
            enable_ssl_verification=os.getenv("MESHMIND_SSL_VERIFY", "true").lower()
            == "true",
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "enable_graceful_degradation": self.enable_graceful_degradation,
            "fallback_on_error": self.fallback_on_error,
            "log_level": self.log_level,
            "enable_structured_logging": self.enable_structured_logging,
            "connection_pool_size": self.connection_pool_size,
            "keepalive_timeout": self.keepalive_timeout,
            "api_key": "***" if self.api_key else None,
            "enable_ssl_verification": self.enable_ssl_verification,
            "tags": self.tags,
        }


@dataclass
class RefereeConfig:
    """Configuration for MeshMind referee service."""

    # Database configuration
    database_url: str = "postgresql://meshmind:meshmind@localhost/meshmind"
    redis_url: str = "redis://localhost:6379"

    # Policy configuration
    policy_file: str = "policy.yaml"
    policy_reload_interval: int = 300  # 5 minutes

    # Performance settings
    max_connections: int = 20
    connection_timeout: float = 30.0

    # Observability settings
    enable_otel: bool = True
    jaeger_endpoint: Optional[str] = None
    metrics_port: int = 9090

    # Security settings
    cors_origins: list = field(default_factory=lambda: ["*"])
    enable_auth: bool = False
    jwt_secret: Optional[str] = None

    @classmethod
    def from_env(cls) -> "RefereeConfig":
        """Create configuration from environment variables."""
        return cls(
            database_url=os.getenv(
                "DATABASE_URL", "postgresql://meshmind:meshmind@localhost/meshmind"
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            policy_file=os.getenv("MESHMIND_POLICY_FILE", "policy.yaml"),
            policy_reload_interval=int(
                os.getenv("MESHMIND_POLICY_RELOAD_INTERVAL", "300")
            ),
            max_connections=int(os.getenv("MESHMIND_MAX_CONNECTIONS", "20")),
            connection_timeout=float(os.getenv("MESHMIND_CONNECTION_TIMEOUT", "30.0")),
            enable_otel=os.getenv("MESHMIND_ENABLE_OTEL", "true").lower() == "true",
            jaeger_endpoint=os.getenv("JAEGER_ENDPOINT"),
            metrics_port=int(os.getenv("MESHMIND_METRICS_PORT", "9090")),
            cors_origins=os.getenv("MESHMIND_CORS_ORIGINS", "*").split(","),
            enable_auth=os.getenv("MESHMIND_ENABLE_AUTH", "false").lower() == "true",
            jwt_secret=os.getenv("MESHMIND_JWT_SECRET"),
        )
