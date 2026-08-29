"""Unit tests for production configuration, environment profiles, validation, and security invariants."""

import math
import os
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment


def test_development_config_defaults():
    """1. Development profile provides accessible defaults with localhost CORS."""
    cfg = DeploymentConfig(environment=DeploymentEnvironment.DEVELOPMENT)
    assert cfg.environment == DeploymentEnvironment.DEVELOPMENT
    assert cfg.port == 8080
    assert cfg.log_level == "INFO"
    assert len(cfg.cors_origins) > 0
    assert "http://localhost:3000" in cfg.cors_origins
    assert cfg.allow_external is False
    assert cfg.hardware_disconnected is True


def test_testing_config_defaults():
    """2. Testing profile initializes with standard testing tier."""
    cfg = DeploymentConfig(environment=DeploymentEnvironment.TESTING)
    assert cfg.environment == DeploymentEnvironment.TESTING
    assert cfg.allow_external is False
    assert cfg.allow_network_download is False


def test_production_config_defaults():
    """3. Production profile strictly disables debug mode and requires explicit CORS."""
    cfg = DeploymentConfig(
        environment=DeploymentEnvironment.PRODUCTION,
        cors_origins=["https://dashboard.skyvanta.ai"],
    )
    assert cfg.environment == DeploymentEnvironment.PRODUCTION
    assert cfg.debug is False
    assert "*" not in cfg.cors_origins
    assert cfg.allow_external is False
    assert cfg.allow_network_download is False
    assert cfg.hardware_disconnected is True


def test_default_safety_settings_immutable():
    """4. Safety invariants remain immutable regardless of constructor inputs."""
    cfg = DeploymentConfig(
        environment=DeploymentEnvironment.DEVELOPMENT,
        allow_external=True,  # Attempt override
        allow_network_download=True,  # Attempt override
        hardware_disconnected=False,  # Attempt override
    )
    assert cfg.allow_external is False
    assert cfg.allow_network_download is False
    assert cfg.hardware_disconnected is True


def test_invalid_port_raises_validation_error():
    """5. Invalid port numbers (< 1 or > 65535) fail fast with ValidationError."""
    with pytest.raises(ValidationError):
        DeploymentConfig(port=0)

    with pytest.raises(ValidationError):
        DeploymentConfig(port=70000)

    with pytest.raises(ValidationError):
        DeploymentConfig(port=-8080)


def test_invalid_telemetry_rate_raises_validation_error():
    """6. Invalid telemetry streaming rate (< 1.0, > 100.0, or NaN) raises ValidationError."""
    with pytest.raises(ValidationError):
        DeploymentConfig(telemetry_rate_hz=0.0)

    with pytest.raises(ValidationError):
        DeploymentConfig(telemetry_rate_hz=150.0)

    with pytest.raises(ValidationError):
        DeploymentConfig(telemetry_rate_hz=float("nan"))


def test_invalid_max_ws_clients_raises_validation_error():
    """7. Invalid WebSocket client bounds (< 1 or > 1000) fail fast."""
    with pytest.raises(ValidationError):
        DeploymentConfig(max_ws_clients=0)

    with pytest.raises(ValidationError):
        DeploymentConfig(max_ws_clients=5000)


def test_invalid_log_level_raises_validation_error():
    """8. Unrecognized log level names raise ValidationError."""
    with pytest.raises(ValidationError):
        DeploymentConfig(log_level="VERBOSE_DEBUG_ALL")


def test_production_wildcard_cors_rejected():
    """9. Production environment strictly rejects wildcard '*' CORS origins."""
    with pytest.raises(ValidationError, match="Wildcard CORS origin"):
        DeploymentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            cors_origins=["*"],
        )


def test_production_debug_mode_rejected():
    """10. Production environment strictly rejects debug=True."""
    with pytest.raises(ValidationError, match="Debug mode must be disabled in production"):
        DeploymentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            debug=True,
        )


def test_environment_variable_overrides(monkeypatch):
    """11. from_env() parses environment variable overrides correctly."""
    monkeypatch.setenv("SKYVANTA_ENV", "testing")
    monkeypatch.setenv("SKYVANTA_PORT", "9090")
    monkeypatch.setenv("SKYVANTA_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SKYVANTA_TELEMETRY_RATE_HZ", "30.0")
    monkeypatch.setenv("SKYVANTA_MAX_WS_CLIENTS", "100")
    monkeypatch.setenv("SKYVANTA_CORS_ORIGINS", "https://app.skyvanta.com, https://ops.skyvanta.com")

    cfg = DeploymentConfig.from_env()
    assert cfg.environment == DeploymentEnvironment.TESTING
    assert cfg.port == 9090
    assert cfg.log_level == "DEBUG"
    assert cfg.telemetry_rate_hz == 30.0
    assert cfg.max_ws_clients == 100
    assert "https://app.skyvanta.com" in cfg.cors_origins
    assert "https://ops.skyvanta.com" in cfg.cors_origins


def test_safety_invariants_cannot_be_overridden_via_env(monkeypatch):
    """12. from_env() enforces False for hardware access and model downloads despite env flags."""
    monkeypatch.setenv("SKYVANTA_ALLOW_EXTERNAL", "true")
    monkeypatch.setenv("SKYVANTA_ALLOW_NETWORK_DOWNLOAD", "true")
    monkeypatch.setenv("SKYVANTA_HARDWARE_ACCESS", "true")

    cfg = DeploymentConfig.from_env()
    assert cfg.allow_external is False
    assert cfg.allow_network_download is False
    assert cfg.hardware_disconnected is True


def test_configuration_serialization():
    """13. DeploymentConfig serializes cleanly to dict and JSON with non-sensitive fields."""
    cfg = DeploymentConfig(
        environment=DeploymentEnvironment.PRODUCTION,
        cors_origins=["https://secure.skyvanta.io"],
    )
    dump = cfg.model_dump()
    assert dump["environment"] == "production"
    assert dump["port"] == 8080
    assert dump["allow_external"] is False
    assert "password" not in str(dump)
    assert "secret" not in str(dump)


def test_security_headers_middleware_integration():
    """14. API responses include standard defensive HTTP security headers."""
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_max_ws_clients_enforcement():
    """15. WebSocket endpoint rejects connections when max_ws_clients limit is reached."""
    app = create_app(
        DeploymentConfig(
            environment=DeploymentEnvironment.TESTING,
            max_ws_clients=1,
        )
    )
    client = TestClient(app)

    # First client occupies the single allowed slot
    with client.websocket_connect("/api/v1/telemetry/ws") as ws1:
        _ = ws1.receive_json()

        # Second client attempts connection while slot is full
        with client.websocket_connect("/api/v1/telemetry/ws") as ws2:
            resp = ws2.receive_json()
            assert resp["type"] == "error"
            assert resp["code"] == "MAX_CLIENTS_EXCEEDED"
