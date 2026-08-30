"""Unit tests for centralized API error handling and validation."""

import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment


@pytest.fixture
def client():
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer sk_test_admin_key_12345"
    return c


def test_invalid_json_body_returns_422(client):
    """POST /api/v1/scenarios/run with invalid types must return 422 validation_error."""
    invalid_payload = {
        "scenario_name": 12345,  # Expected string
        "seed": "not_an_int",    # Expected int
    }
    response = client.post("/api/v1/scenarios/run", json=invalid_payload)
    assert response.status_code == 422
    data = response.json()

    assert data["error"] == "validation_error"
    assert "details" in data
    assert "request_id" in data


def test_run_unknown_scenario_returns_404(client):
    """POST /api/v1/scenarios/run for a missing scenario must return 404 scenario_not_found."""
    payload = {
        "scenario_name": "unknown_scenario_abc",
        "seed": 42,
    }
    response = client.post("/api/v1/scenarios/run", json=payload)
    assert response.status_code == 404
    data = response.json()

    assert data["error"] == "scenario_not_found"
    assert "unknown_scenario_abc" in data["message"]
    assert "request_id" in data


def test_cors_headers(client):
    """OPTIONS preflight or cross-origin requests must include configured CORS headers."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
