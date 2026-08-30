"""Unit tests for the /api/v1/metrics operational monitoring endpoint."""

import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.observability.metrics import metrics_collector


@pytest.fixture
def client():
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer sk_test_admin_key_12345"
    return c


def test_metrics_endpoint_structure(client):
    """GET /api/v1/metrics must return comprehensive machine-readable metrics schema."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()

    assert data["service"] == "skyvanta-api"
    assert "version" in data
    assert data["environment"] == "testing"
    assert "timestamp_sec" in data

    # 1. HTTP Metrics
    assert "http" in data
    http = data["http"]
    assert "total_requests" in http
    assert "successful_requests" in http
    assert "failed_requests" in http
    assert "requests_by_method" in http
    assert "requests_by_endpoint" in http
    assert "requests_by_status" in http
    assert "latency_overall" in http
    lat = http["latency_overall"]
    assert "min_ms" in lat
    assert "avg_ms" in lat
    assert "median_ms" in lat
    assert "p95_ms" in lat
    assert "p99_ms" in lat
    assert "max_ms" in lat

    # 2. Error Metrics
    assert "errors" in data
    errors = data["errors"]
    assert "validation_errors" in errors
    assert "scenario_execution_failures" in errors
    assert "internal_errors" in errors
    assert "websocket_errors" in errors

    # 3. WebSocket Metrics
    assert "websockets" in data
    ws = data["websockets"]
    assert "active_connections" in ws
    assert "total_connections" in ws
    assert "telemetry_packets_sent" in ws
    assert "configured_stream_rate_hz" in ws
    assert "observed_stream_rate_hz" in ws

    # 4. Scenario Metrics
    assert "scenarios" in data
    scenarios = data["scenarios"]
    assert "total_executions" in scenarios
    assert "successful_executions" in scenarios

    # 5. System Resources
    assert "system" in data
    sys_metrics = data["system"]
    assert "uptime_sec" in sys_metrics
    assert "cpu_percent" in sys_metrics
    assert "memory_rss_mb" in sys_metrics
    assert "python_version" in sys_metrics
    assert "git_commit" in sys_metrics

    # 6. Warnings & Events
    assert isinstance(data["warnings"], list)
    assert isinstance(data["recent_events"], list)


def test_metrics_dynamic_update_after_scenario_run(client):
    """Executing a scenario must update scenario execution metrics dynamically."""
    payload = {
        "scenario_name": "nominal_landing",
        "seed": 42,
        "max_duration_sec": 1.0,
    }
    run_resp = client.post("/api/v1/scenarios/run", json=payload)
    assert run_resp.status_code == 200

    metrics_resp = client.get("/api/v1/metrics")
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()

    assert metrics_data["scenarios"]["total_executions"] >= 1
    assert "nominal_landing" in metrics_data["scenarios"]["scenarios"]


def test_metrics_no_secrets_exposed(client):
    """GET /api/v1/metrics must not leak passwords, tokens, API keys, or private files."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    text_content = response.text.lower()

    forbidden_terms = ["password", "secret_key", "private_key", "bearer eyj", "api_key="]
    for term in forbidden_terms:
        assert term not in text_content
