"""Production deployment configuration, environment profiles, and validation models."""

from enum import Enum
import math
import os
import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class DeploymentEnvironment(str, Enum):
    """Runtime deployment environment tiers."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class DeploymentConfig(BaseModel):
    """Production deployment configuration with strict safety defaults and validation."""

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
        ge=1,
        le=65535,
        description="Bind port for API server (1-65535).",
    )
    log_level: str = Field(
        default="INFO",
        description="Structured deployment logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).",
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
        description="Allowed CORS origin URLs for dashboard / client access.",
    )
    telemetry_rate_hz: float = Field(
        default=20.0,
        ge=1.0,
        le=100.0,
        description="Maximum streaming rate for telemetry WebSocket broadcast in Hz (1.0 - 100.0).",
    )
    max_ws_clients: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum simultaneous WebSocket telemetry connections.",
    )
    request_timeout_sec: float = Field(
        default=60.0,
        ge=1.0,
        le=600.0,
        description="HTTP request processing timeout in seconds.",
    )
    ws_idle_timeout_sec: float = Field(
        default=300.0,
        ge=5.0,
        le=3600.0,
        description="WebSocket idle connection timeout in seconds.",
    )
    enable_metrics: bool = Field(
        default=True,
        description="Whether to enable operational metrics endpoints.",
    )
    enable_security_headers: bool = Field(
        default=True,
        description="Whether to attach HTTP security headers (X-Content-Type-Options, etc.).",
    )
    debug: bool = Field(
        default=False,
        description="Debug mode (strictly prohibited in production).",
    )

    # Immutable Safety & Hardware Isolation Invariants
    allow_external: bool = Field(
        default=False,
        description="Strict safety invariant: Physical or external actuation is prohibited.",
    )
    allow_network_download: bool = Field(
        default=False,
        description="Strict safety invariant: Automatic runtime model downloads are prohibited.",
    )
    hardware_disconnected: bool = Field(
        default=True,
        description="Strict safety invariant: Hardware serial/MAVLink ports are permanently disconnected.",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validates that log level is an approved standard level."""
        v_upper = v.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v_upper not in allowed:
            raise ValueError(f"Invalid log_level '{v}'. Must be one of {sorted(allowed)}")
        return v_upper

    @field_validator("telemetry_rate_hz")
    @classmethod
    def validate_telemetry_rate(cls, v: float) -> float:
        """Validates that telemetry rate is finite and within bounded range."""
        if not math.isfinite(v) or math.isnan(v):
            raise ValueError("telemetry_rate_hz must be a finite real number.")
        if v < 1.0 or v > 100.0:
            raise ValueError("telemetry_rate_hz must be between 1.0 and 100.0 Hz.")
        return float(v)

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        """Validates that CORS origins list contains valid non-empty URLs/origins."""
        cleaned = []
        for origin in v:
            orig_str = origin.strip()
            if not orig_str:
                continue
            if orig_str != "*" and not (orig_str.startswith("http://") or orig_str.startswith("https://")):
                raise ValueError(f"Invalid CORS origin '{origin}': Must start with http:// or https://")
            cleaned.append(orig_str)
        return cleaned

    @model_validator(mode="after")
    def validate_production_invariants(self) -> "DeploymentConfig":
        """Enforces hard invariants for production environments."""
        if self.environment == DeploymentEnvironment.PRODUCTION:
            if self.debug:
                raise ValueError("Debug mode must be disabled in production.")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS origin '*' is strictly prohibited in production.")
        
        # Hard safety enforcement across all deployment tiers
        self.allow_external = False
        self.allow_network_download = False
        self.hardware_disconnected = True
        return self

    @classmethod
    def from_env(cls) -> "DeploymentConfig":
        """Constructs deployment config from environment variables with safe fallbacks."""
        env_str = os.getenv("SKYVANTA_ENV", "development").lower().strip()
        try:
            env = DeploymentEnvironment(env_str)
        except ValueError:
            env = DeploymentEnvironment.DEVELOPMENT

        host = os.getenv("SKYVANTA_HOST", "0.0.0.0").strip()

        port_raw = os.getenv("PORT") or os.getenv("SKYVANTA_PORT", "8080")
        try:
            port = int(port_raw)
        except ValueError:
            port = 8080

        log_level = os.getenv("SKYVANTA_LOG_LEVEL", "INFO").upper().strip()

        cors_raw = os.getenv("SKYVANTA_CORS_ORIGINS") or os.getenv("SKYVANTA_ALLOWED_ORIGINS", "")
        if cors_raw.strip():
            cors_origins = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]
        elif env == DeploymentEnvironment.PRODUCTION:
            cors_origins = []
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

        try:
            max_ws_clients = int(os.getenv("SKYVANTA_MAX_WS_CLIENTS", "50"))
        except ValueError:
            max_ws_clients = 50

        try:
            req_timeout = float(os.getenv("SKYVANTA_REQUEST_TIMEOUT_SEC", "60.0"))
        except ValueError:
            req_timeout = 60.0

        try:
            ws_idle_timeout = float(os.getenv("SKYVANTA_WS_IDLE_TIMEOUT_SEC", "300.0"))
        except ValueError:
            ws_idle_timeout = 300.0

        enable_metrics = os.getenv("SKYVANTA_ENABLE_METRICS", "true").lower() in ("true", "1", "yes")
        enable_security_headers = os.getenv("SKYVANTA_ENABLE_SECURITY_HEADERS", "true").lower() in ("true", "1", "yes")
        debug = os.getenv("SKYVANTA_DEBUG", "false").lower() in ("true", "1", "yes")

        # In production, debug is strictly False
        if env == DeploymentEnvironment.PRODUCTION:
            debug = False

        return cls(
            environment=env,
            host=host,
            port=port,
            log_level=log_level,
            cors_origins=cors_origins,
            telemetry_rate_hz=telemetry_rate,
            max_ws_clients=max_ws_clients,
            request_timeout_sec=req_timeout,
            ws_idle_timeout_sec=ws_idle_timeout,
            enable_metrics=enable_metrics,
            enable_security_headers=enable_security_headers,
            debug=debug,
            # Immutable safety invariants
            allow_external=False,
            allow_network_download=False,
            hardware_disconnected=True,
        )
