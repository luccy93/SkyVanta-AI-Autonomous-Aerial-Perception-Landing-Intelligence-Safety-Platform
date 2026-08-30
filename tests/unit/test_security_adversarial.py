"""Adversarial security attack simulation tests and defensive validation."""

import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.security.audit import security_audit_logger, SecurityEventType
from skyvanta.deployment.security.redaction import mask_api_key, sanitize_headers, sanitize_payload


@pytest.fixture
def client():
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer sk_test_admin_key_12345"
    return c


def test_malformed_json_rejected_cleanly(client):
    """1. Malformed JSON payload is rejected with 422 and does not crash the server."""
    response = client.post(
        "/api/v1/scenarios/run",
        content="{\"scenario_name\": \"nominal_landing\", invalid_json...}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code in (400, 422)


def test_nan_infinity_values_rejected(client):
    """2. Non-finite floating point inputs (NaN, Inf) are rejected by contract validation."""
    payload_nan = {
        "scenario_name": "nominal_landing",
        "seed": 42,
        "max_duration_sec": float("nan"),
    }
    # JSON does not represent NaN natively; client sends string or null or rejected
    response = client.post("/api/v1/scenarios/run", json={"scenario_name": "nominal_landing", "seed": 42, "max_duration_sec": "NaN"})
    assert response.status_code == 422


def test_negative_values_rejected(client):
    """3. Negative parameters where prohibited (e.g. max_duration_sec <= 0) are rejected."""
    payload = {
        "scenario_name": "nominal_landing",
        "seed": 42,
        "max_duration_sec": -10.0,
    }
    response = client.post("/api/v1/scenarios/run", json=payload)
    assert response.status_code == 422


def test_error_response_no_stack_traces_or_paths(client):
    """4. 4xx error responses do not leak local disk paths or internal stack traces."""
    response = client.get("/api/v1/scenarios/non_existent_12345")
    assert response.status_code == 404
    data = response.json()

    raw_text = str(data).lower()
    assert "traceback" not in raw_text
    assert "c:\\" not in raw_text
    assert "/home/" not in raw_text
    assert ".py\"," not in raw_text


def test_audit_logging_scrubs_secrets():
    """5. Security audit logging scrubs raw credentials from event payloads."""
    event = security_audit_logger.record(
        event_type=SecurityEventType.AUTH_FAILURE,
        message="Test failed auth",
        details={
            "api_key": "sk_live_super_secret_key_12345",
            "password": "mypassword123",
            "headers": {"Authorization": "Bearer sk_secret_token"},
        },
    )

    dump = event.model_dump()
    details = dump["details"]
    assert details["api_key"] == "[REDACTED]"
    assert details["password"] == "[REDACTED]"
    assert details["headers"]["Authorization"] == "[REDACTED]"
    assert "mypassword123" not in str(dump)
    assert "sk_live_super_secret_key_12345" not in str(dump)
