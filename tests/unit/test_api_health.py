"""Unit tests for the /health infrastructure endpoint."""

import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment


@pytest.fixture
def client():
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    return TestClient(app)


def test_health_endpoint_success(client):
    """GET /health must return 200 OK with healthy status and verified safety invariants."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "skyvanta-api"
    assert data["simulation_engine"] == "ready"
    assert data["available_scenarios_count"] >= 10
    assert data["hardware_access"] is False
    assert data["network_model_download"] is False
    assert data["safety_boundary_enforced"] is True
    assert "uptime_sec" in data
    assert "timestamp_sec" in data
    assert "X-Request-ID" in response.headers


def test_health_endpoint_correlation_header(client):
    """Passing custom X-Request-ID header must be preserved in response."""
    custom_id = "custom_test_trace_12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id
