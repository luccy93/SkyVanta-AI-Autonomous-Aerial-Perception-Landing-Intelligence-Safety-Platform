"""Unit tests for request payload and header size limiter middleware."""

import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment


@pytest.fixture
def app_with_small_limits():
    """App configured with strict 1 KB body and 1 KB header limits for testing."""
    config = DeploymentConfig(
        environment=DeploymentEnvironment.TESTING,
        max_request_body_bytes=1024,      # 1 KB
        max_request_header_bytes=1024,    # 1 KB
    )
    return create_app(config)


def test_payload_under_limit_accepted(app_with_small_limits):
    """1. Payloads under the size threshold are processed normally."""
    client = TestClient(app_with_small_limits)
    client.headers["Authorization"] = "Bearer sk_test_admin_key_12345"

    small_payload = {"scenario_name": "nominal_landing", "seed": 42, "max_duration_sec": 1.0}
    response = client.post("/api/v1/scenarios/run", json=small_payload)
    assert response.status_code == 200


def test_payload_exceeding_limit_rejected_with_413(app_with_small_limits):
    """2. Request bodies larger than limit are rejected with 413 Payload Too Large."""
    client = TestClient(app_with_small_limits)
    client.headers["Authorization"] = "Bearer sk_test_admin_key_12345"

    # Create > 1KB payload
    oversized_payload = {
        "scenario_name": "nominal_landing",
        "seed": 42,
        "padding": "x" * 2048,  # 2 KB
    }
    response = client.post("/api/v1/scenarios/run", json=oversized_payload)
    assert response.status_code == 413
    assert "exceeds maximum allowable limit" in response.json()["detail"]


def test_headers_exceeding_limit_rejected_with_431(app_with_small_limits):
    """3. Oversized request headers are rejected with 431 Request Header Fields Too Large."""
    client = TestClient(app_with_small_limits)

    # 2 KB header
    custom_headers = {
        "Authorization": "Bearer sk_test_admin_key_12345",
        "X-Custom-Bloat": "h" * 2048,
    }
    response = client.get("/health", headers=custom_headers)
    assert response.status_code == 431
    assert "exceed maximum allowable size" in response.json()["detail"]
