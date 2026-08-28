"""Deployment configuration management and environment isolation models."""

import os
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DeploymentEnvironment(str, Enum):
    """Runtime deployment environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class DeploymentConfig(BaseModel):
    """Production deployment configuration with strict safety defaults."""

    environment: DeploymentEnvironment = Field(
        default=DeploymentEnvironment.DEVELOPMENT,
        description="Active deployment tier (development, testing, production).",
    )
    host: str = Field(
        default="0.0.0.0",
        description="Bind host IP address for API server.",
    )
    port: int = Field(
        default=8080,
        description="Bind port for API server.",
    )
    log_level: str = Field(
        default="INFO",
        description="Structured deployment logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
        description="Allowed CORS origin URLs for future dashboard integration.",
    )
    telemetry_rate_hz: float = Field(
        default=20.0,
        description="Maximum streaming rate for telemetry WebSocket broadcast.",
    )
    enable_metrics: bool = Field(
        default=True,
        description="Whether to expose Prometheus/OpenTelemetry metrics endpoints.",
    )

    # Immutable Safety & Hardware Isolation Invariants
    allow_external: bool = Field(
        default=False,
        description="Strict safety invariant: Physical or external network actuation is prohibited.",
    )
    allow_network_download: bool = Field(
        default=False,
        description="Strict safety invariant: Automatic runtime model downloads are prohibited.",
    )
    hardware_disconnected: bool = Field(
        default=True,
        description="Strict safety invariant: Hardware serial/MAVLink ports are permanently disconnected.",
    )

    @classmethod
    def from_env(cls) -> "DeploymentConfig":
        """Constructs deployment config from environment variables with safe fallbacks."""
        env_str = os.getenv("SKYVANTA_ENV", "development").lower()
        try:
            env = DeploymentEnvironment(env_str)
        except ValueError:
            env = DeploymentEnvironment.DEVELOPMENT

        host = os.getenv("SKYVANTA_HOST", "0.0.0.0")
        
        try:
            port = int(os.getenv("SKYVANTA_PORT", "8080"))
        except ValueError:
            port = 8080

        log_level = os.getenv("SKYVANTA_LOG_LEVEL", "INFO").upper()

        cors_raw = os.getenv("SKYVANTA_CORS_ORIGINS", "")
        if cors_raw.strip():
            cors_origins = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]
        else:
            cors_origins = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
            ]

        try:
            telemetry_rate = float(os.getenv("SKYVANTA_TELEMETRY_RATE_HZ", "20.0"))
        except ValueError:
            telemetry_rate = 20.0

        enable_metrics = os.getenv("SKYVANTA_ENABLE_METRICS", "true").lower() in ("true", "1", "yes")

        return cls(
            environment=env,
            host=host,
            port=port,
            log_level=log_level,
            cors_origins=cors_origins,
            telemetry_rate_hz=telemetry_rate,
            enable_metrics=enable_metrics,
            # Safety invariants remain strictly false/true regardless of env
            allow_external=False,
            allow_network_download=False,
            hardware_disconnected=True,
        )
