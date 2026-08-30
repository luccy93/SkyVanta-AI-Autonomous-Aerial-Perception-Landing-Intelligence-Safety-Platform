"""Comprehensive deployment smoke tests and failure-injection verification suite."""

import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.health import HealthCheckService
from skyvanta.deployment.release import ReleaseVerifier, ReleaseManifest
from skyvanta.deployment.reliability import (
    FailureCategory,
    RecoveryAction,
    RecoveryManager,
    ShutdownCoordinator,
    StartupValidationError,
    StartupValidator,
)


@pytest.fixture
def test_client():
    """Authenticated TestClient fixture for smoke tests."""
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer sk_test_admin_key_12345"
    return c


@pytest.fixture
def unauth_client():
    """Unauthenticated TestClient fixture."""
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    return TestClient(app)


# ------------------------------------------------------------------------------
# 1. HTTP Endpoint Smoke Tests
# ------------------------------------------------------------------------------

def test_smoke_health_endpoint(unauth_client):
    """Smoke: /health returns 200 OK without credentials and enforces safety."""
    resp = unauth_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["hardware_access"] is False
    assert data["network_model_download"] is False
    assert data["safety_boundary_enforced"] is True


def test_smoke_readiness_endpoint(unauth_client):
    """Smoke: /ready returns 200 OK and confirms operational dependencies."""
    resp = unauth_client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert data["status"] == "ready"


def test_smoke_system_info_endpoint(test_client):
    """Smoke: /api/v1/system/info returns capabilities and version metadata."""
    resp = test_client.get("/api/v1/system/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["application"] == "SkyVanta AI"
    assert data["hardware_access"] is False
    assert data["network_model_download"] is False


def test_smoke_scenarios_catalog_endpoint(test_client):
    """Smoke: /api/v1/scenarios returns benchmark landing scenarios."""
    resp = test_client.get("/api/v1/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 10
    scenario_names = [s["name"] for s in data]
    assert "nominal_landing" in scenario_names


def test_smoke_release_endpoint(test_client):
    """Smoke: /api/v1/release returns verified release metadata."""
    resp = test_client.get("/api/v1/release")
    assert resp.status_code == 200
    data = resp.json()
    assert data["application"] == "SkyVanta AI"
    assert data["core_version"] == "V1-V9"
    assert data["release_verified"] is True
    assert data["hardware_access"] is False
    assert data["network_model_download"] is False


# ------------------------------------------------------------------------------
# 2. WebSocket Telemetry Smoke Test
# ------------------------------------------------------------------------------

def test_smoke_telemetry_websocket():
    """Smoke: /api/v1/telemetry/ws admits authenticated client and streams packets."""
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    client = TestClient(app)

    with client.websocket_connect(
        "/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20",
        headers={"Authorization": "Bearer sk_test_admin_key_12345"},
    ) as ws:
        packet = ws.receive_json()
        assert packet is not None
        assert "timestamp_sim_sec" in packet or "packet_type" in packet
        if "position_m" in packet:
            assert len(packet["position_m"]) == 3
            assert packet["is_safe"] is True


# ------------------------------------------------------------------------------
# 3. Security Boundary Verification
# ------------------------------------------------------------------------------

def test_smoke_security_unauthenticated_blocked(unauth_client):
    """Smoke: Protected endpoints reject unauthenticated access with 401."""
    assert unauth_client.get("/api/v1/system/info").status_code == 401
    assert unauth_client.get("/api/v1/scenarios").status_code == 401
    assert unauth_client.get("/api/v1/release").status_code == 401
    assert unauth_client.get("/api/v1/metrics").status_code == 401


# ------------------------------------------------------------------------------
# 4. Failure-Injection Verification
# ------------------------------------------------------------------------------

def test_failure_injection_startup_invalid_safety():
    """Failure Injection: Invalid safety flag prevents application boot."""
    validator = StartupValidator()
    dep_cfg = DeploymentConfig()
    dep_cfg.hardware_disconnected = False

    with pytest.raises(StartupValidationError):
        validator.validate_or_raise(deployment_config=dep_cfg)


def test_failure_injection_startup_malformed_manifest():
    """Failure Injection: Blank or corrupted manifest fails pre-flight verification."""
    verifier = ReleaseVerifier()
    bad_manifest = ReleaseManifest(version="")
    result = verifier.verify(manifest=bad_manifest)
    assert result.passed is False
    assert result.checks["version_valid"] is False


def test_failure_injection_recovery_unsafe_config():
    """Failure Injection: Unsafe configuration locks recovery policy."""
    mgr = RecoveryManager()
    decision = mgr.handle_failure(
        exception=StartupValidationError("Safety Violation: allow_external is enabled"),
    )
    assert decision.category == FailureCategory.SAFETY_CONFIGURATION_FAILURE
    assert decision.action == RecoveryAction.BLOCK_RECOVERY
    assert decision.recovery_blocked is True
    assert decision.hardware_activation_prohibited is True


@pytest.mark.asyncio
async def test_failure_injection_repeated_shutdown():
    """Failure Injection: Repeated shutdown invocation is idempotent and safe."""
    coordinator = ShutdownCoordinator()
    res1 = await coordinator.initiate_shutdown(timeout_sec=1.0)
    res2 = await coordinator.initiate_shutdown(timeout_sec=1.0)
    assert res1.success is True
    assert res2.success is True
    assert coordinator.is_shutdown_complete is True
