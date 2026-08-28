"""Unit tests for the /api/v1/system/info endpoint."""

import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment


@pytest.fixture
def client():
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    return TestClient(app)


def test_system_info_endpoint(client):
    """GET /api/v1/system/info must return valid application metadata and capabilities."""
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    data = response.json()

    assert data["application"] == "SkyVanta AI"
    assert data["api_version"] == "v1"
    assert data["environment"] == "testing"
    assert data["hardware_access"] is False
    assert data["network_model_download"] is False
    assert data["safety_boundary_enforced"] is True
    assert isinstance(data["supported_capabilities"], list)
    assert len(data["supported_capabilities"]) > 0
    assert "6_dof_digital_twin_simulation" in data["supported_capabilities"]
    assert "15_state_esekf_sensor_fusion" in data["supported_capabilities"]
    assert "X-Request-ID" in response.headers
