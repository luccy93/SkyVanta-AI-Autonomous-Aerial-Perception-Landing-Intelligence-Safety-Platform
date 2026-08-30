"""Unit tests for scenario catalog and closed-loop execution endpoints."""

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


def test_list_scenarios(client):
    """GET /api/v1/scenarios must list all registered benchmark scenarios."""
    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    catalog = response.json()

    assert isinstance(catalog, list)
    assert len(catalog) >= 10
    names = [s["name"] for s in catalog]
    assert "nominal_landing" in names
    assert "target_loss" in names


def test_get_scenario_details(client):
    """GET /api/v1/scenarios/{name} must return full kinematic and event parameters."""
    response = client.get("/api/v1/scenarios/nominal_landing")
    assert response.status_code == 200
    details = response.json()

    assert details["name"] == "nominal_landing"
    assert "initial_vehicle_pos" in details
    assert "initial_vehicle_vel" in details
    assert isinstance(details["events"], list)


def test_get_unknown_scenario_returns_404(client):
    """GET /api/v1/scenarios/{unknown} must return 404 with structured error."""
    response = client.get("/api/v1/scenarios/non_existent_scenario_xyz")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "message" in data
    assert "request_id" in data


def test_run_nominal_scenario_execution(client):
    """POST /api/v1/scenarios/run must execute closed-loop digital twin simulation."""
    payload = {
        "scenario_name": "nominal_landing",
        "seed": 42,
        "max_duration_sec": 5.0,
    }
    response = client.post("/api/v1/scenarios/run", json=payload)
    assert response.status_code == 200
    result = response.json()

    assert result["seed"] == 42
    assert result["duration_sim_sec"] > 0.0
    assert result["duration_wall_sec"] >= 0.0
    assert result["realtime_factor"] > 0.0
    assert result["safety_violations_count"] == 0
    assert "final_position_error_m" in result
    assert "rmse_position_m" in result
