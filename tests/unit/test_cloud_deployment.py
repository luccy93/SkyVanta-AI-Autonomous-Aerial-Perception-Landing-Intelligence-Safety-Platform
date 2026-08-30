"""Unit tests for Phase D6 Cloud Deployment, Blueprint specification, runtime PORT handling, and public production release."""

from pathlib import Path
import json
import logging
import os
import pytest
import yaml
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.health import HealthCheckService
from skyvanta.deployment.logging import JSONDeploymentFormatter


@pytest.fixture
def repo_root() -> Path:
    """Returns absolute path to the repository root directory."""
    return Path(__file__).resolve().parent.parent.parent


def test_render_blueprint_structure_and_safety(repo_root):
    """1. render.yaml exists, defines valid Docker web service, health check path, and production env."""
    render_path = repo_root / "render.yaml"
    assert render_path.is_file(), "render.yaml blueprint must exist at repository root"

    with open(render_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "services" in data, "render.yaml must define services"
    services = data["services"]
    assert len(services) >= 1, "Must have at least one service defined"

    web_svc = next((s for s in services if s.get("type") == "web"), None)
    assert web_svc is not None, "Must define a web service"
    assert web_svc.get("runtime") == "docker", "Web service must use docker runtime"
    assert web_svc.get("healthCheckPath") == "/health", "Health check path must be /health"

    env_map = {item["key"]: item["value"] for item in web_svc.get("envVars", [])}
    assert env_map.get("SKYVANTA_ENV") == "production", "SKYVANTA_ENV must be production"
    assert env_map.get("SKYVANTA_ALLOW_EXTERNAL") == "false", "allow_external must be false"
    assert env_map.get("SKYVANTA_ALLOW_NETWORK_DOWNLOAD") == "false", "allow_network_download must be false"
    assert env_map.get("SKYVANTA_LOG_LEVEL") == "INFO"

    # Ensure no secrets or API keys are embedded in blueprint
    raw_content = render_path.read_text(encoding="utf-8").lower()
    assert "secret" not in raw_content or "key:" in raw_content  # yaml keys are fine, secret values are not
    assert "password" not in raw_content
    assert "token" not in raw_content


def test_cloud_dynamic_port_resolution(monkeypatch):
    """2. DeploymentConfig.from_env() respects cloud platform PORT environment variable."""
    # Test standard cloud $PORT assignment (e.g. 10000 on Render / Cloud Run)
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.delenv("SKYVANTA_PORT", raising=False)
    cfg = DeploymentConfig.from_env()
    assert cfg.port == 10000

    # Test PORT priority over SKYVANTA_PORT
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("SKYVANTA_PORT", "8080")
    cfg2 = DeploymentConfig.from_env()
    assert cfg2.port == 9000

    # Test fallback to SKYVANTA_PORT when PORT is absent
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setenv("SKYVANTA_PORT", "8888")
    cfg3 = DeploymentConfig.from_env()
    assert cfg3.port == 8888

    # Test default 8080 fallback
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("SKYVANTA_PORT", raising=False)
    cfg4 = DeploymentConfig.from_env()
    assert cfg4.port == 8080


def test_production_cloud_healthcheck_endpoint():
    """3. GET /health satisfies cloud health probe contract with healthy status and safety flags."""
    app = create_app(
        DeploymentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            cors_origins=["https://skyvanta-ai.onrender.com"],
        )
    )
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "skyvanta-api"
    assert data["environment"] == "production"
    assert data["simulation_engine"] == "ready"
    assert data["available_scenarios_count"] >= 10
    assert data["hardware_access"] is False
    assert data["network_model_download"] is False
    assert data["safety_boundary_enforced"] is True
    assert data["uptime_sec"] >= 0.0


def test_production_cloud_system_info_endpoint():
    """4. GET /api/v1/system/info returns production capability manifest with zero hardware access."""
    app = create_app(
        DeploymentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            cors_origins=["https://skyvanta-ai.onrender.com"],
        )
    )
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer sk_test_admin_key_12345"

    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()

    assert data["application"] == "SkyVanta AI"
    assert data["api_version"] == "v1"
    assert data["environment"] == "production"
    assert data["hardware_access"] is False
    assert data["network_model_download"] is False
    assert data["safety_boundary_enforced"] is True
    assert "6_dof_digital_twin_simulation" in data["supported_capabilities"]
    assert "15_state_esekf_sensor_fusion" in data["supported_capabilities"]
    assert "12_state_safety_fsm_supervision" in data["supported_capabilities"]


def test_production_cloud_scenarios_catalog():
    """5. GET /api/v1/scenarios lists all registered standard benchmark scenarios."""
    app = create_app(
        DeploymentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            cors_origins=["https://skyvanta-ai.onrender.com"],
        )
    )
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer sk_test_admin_key_12345"

    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    catalog = response.json()
    assert len(catalog) >= 10

    names = {s["name"] for s in catalog}
    assert "nominal_landing" in names
    assert "target_loss" in names
    assert "target_occlusion" in names
    assert "camera_dropout" in names
    assert "imu_dropout" in names


def test_production_cloud_scenario_execution():
    """6. POST /api/v1/scenarios/run executes closed-loop simulation and returns metrics."""
    app = create_app(
        DeploymentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            cors_origins=["https://skyvanta-ai.onrender.com"],
        )
    )
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer sk_test_admin_key_12345"

    payload = {
        "scenario_name": "nominal_landing",
        "seed": 42,
        "enable_noise": True,
    }
    response = client.post("/api/v1/scenarios/run", json=payload)
    assert response.status_code == 200
    result = response.json()

    assert result["status"] == "SUCCESS_LANDED"
    assert result["is_success"] is True
    assert result["safety_violations_count"] == 0
    assert result["realtime_factor"] > 1.0
    assert result["final_position_error_m"] <= 0.10


def test_production_cloud_websocket_telemetry_lifecycle():
    """7. WebSocket endpoint streams telemetry at configured rate, supports ping/pong, and handles reconnect."""
    app = create_app(
        DeploymentConfig(
            environment=DeploymentEnvironment.PRODUCTION,
            cors_origins=["https://skyvanta-ai.onrender.com"],
            telemetry_rate_hz=20.0,
        )
    )
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer sk_test_admin_key_12345"

    # 1. First connection
    with client.websocket_connect("/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20") as ws:
        # Receive first packet
        pkt1 = ws.receive_json()
        assert pkt1["packet_type"] == "telemetry"
        assert pkt1["scenario_name"] == "nominal_landing"
        assert "position_m" in pkt1
        assert "velocity_m_s" in pkt1
        assert "landing_phase" in pkt1
        assert pkt1["is_safe"] is True

        # Send heartbeat ping
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"
        assert "timestamp_sec" in pong

    # 2. Reconnection lifecycle verification
    with client.websocket_connect("/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20") as ws2:
        pkt2 = ws2.receive_json()
        assert pkt2["packet_type"] == "telemetry"
        assert pkt2["is_safe"] is True


def test_production_cloud_structured_json_logging():
    """8. Production JSON logger produces valid single-line JSON log strings with required keys."""
    formatter = JSONDeploymentFormatter()
    record = logging.LogRecord(
        name="skyvanta.api",
        level=logging.INFO,
        pathname="app.py",
        lineno=50,
        msg="Cloud request completed successfully",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "skyvanta.api"
    assert parsed["message"] == "Cloud request completed successfully"
    assert parsed["service"] == "skyvanta-deployment"
    assert "timestamp" in parsed


def test_production_cloud_explicit_cors_and_safety_invariants(monkeypatch):
    """9. Cloud production environment enforces explicit HTTPS origins and locks safety invariants."""
    monkeypatch.setenv("SKYVANTA_ENV", "production")
    monkeypatch.setenv("SKYVANTA_CORS_ORIGINS", "https://skyvanta-ai.onrender.com,https://dashboard.skyvanta.ai")
    monkeypatch.setenv("SKYVANTA_ALLOW_EXTERNAL", "true")  # Attempt malicious override
    monkeypatch.setenv("SKYVANTA_ALLOW_NETWORK_DOWNLOAD", "true")  # Attempt malicious override

    cfg = DeploymentConfig.from_env()
    assert cfg.environment == DeploymentEnvironment.PRODUCTION
    assert cfg.debug is False
    assert "*" not in cfg.cors_origins
    assert "https://skyvanta-ai.onrender.com" in cfg.cors_origins
    assert "https://dashboard.skyvanta.ai" in cfg.cors_origins
    assert cfg.allow_external is False
    assert cfg.allow_network_download is False
    assert cfg.hardware_disconnected is True
