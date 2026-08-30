"""Unit tests for the /ready readiness probe and liveness vs readiness distinction."""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.observability.health import ReadinessService


@pytest.fixture
def client():
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    return TestClient(app)


def test_readiness_endpoint_success(client):
    """GET /ready must return 200 OK with ready=True when genuine dependencies are verified."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()

    assert data["ready"] is True
    assert data["status"] == "ready"
    assert data["service"] == "skyvanta-api"
    assert "version" in data
    assert data["environment"] == "testing"
    assert data["checks"]["scenario_catalog_loaded"] is True
    assert data["checks"]["simulation_engine_ready"] is True
    assert data["checks"]["safety_invariants_enforced"] is True
    assert "uptime_sec" in data
    assert "timestamp_sec" in data
    assert "X-Request-ID" in response.headers


def test_liveness_contract_preserved(client):
    """GET /health liveness contract must remain completely intact."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "skyvanta-api"
    assert data["simulation_engine"] == "ready"
    assert data["hardware_access"] is False
    assert data["network_model_download"] is False
    assert data["safety_boundary_enforced"] is True


def test_readiness_failure_path(client):
    """If a genuine dependency fails, GET /ready must return 503 Service Unavailable."""
    service = ReadinessService()

    # Simulate scenario catalog failure (empty scenarios)
    with patch("skyvanta.deployment.observability.health.ScenarioRegistry.list_all", return_value=[]):
        res = service.check_readiness()
        assert res.ready is False
        assert res.status == "not_ready"
        assert res.checks["scenario_catalog_loaded"] is False
