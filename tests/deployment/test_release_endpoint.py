"""Unit tests for the GET /api/v1/release endpoint."""

import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment


@pytest.fixture
def auth_client():
    """Test client with valid authentication headers."""
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer sk_test_admin_key_12345"
    return c


@pytest.fixture
def anon_client():
    """Unauthenticated test client."""
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    return TestClient(app)


def test_release_endpoint_nominal(auth_client):
    """GET /api/v1/release returns 200 OK with verified release metadata."""
    response = auth_client.get("/api/v1/release")
    assert response.status_code == 200
    data = response.json()

    assert data["application"] == "SkyVanta AI"
    assert data["api_version"] == "v1"
    assert data["environment"] == "testing"
    assert data["core_version"] == "V1-V9"
    assert data["hardware_access"] is False
    assert data["network_model_download"] is False
    assert data["release_verified"] is True
    assert "git_commit" in data
    assert "version" in data
    assert "X-Request-ID" in response.headers


def test_release_endpoint_requires_auth(anon_client):
    """Unauthenticated GET /api/v1/release returns 401 Unauthorized under D8 security."""
    response = anon_client.get("/api/v1/release")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_release_endpoint_invalid_key(anon_client):
    """GET /api/v1/release with invalid key returns 401 Unauthorized."""
    response = anon_client.get(
        "/api/v1/release",
        headers={"Authorization": "Bearer sk_invalid_key_99999"},
    )
    assert response.status_code == 401
