"""Unit tests for endpoint authentication, scope authorization, and status codes."""

import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.security.api_keys import api_key_manager
from skyvanta.deployment.security.policies import Scope


@pytest.fixture
def app_instance():
    return create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))


@pytest.fixture(autouse=True)
def setup_keys():
    # Register deterministic test keys
    api_key_manager.register_raw_key("sk_test_admin_valid", name="admin_user", scopes={Scope.ADMIN})
    api_key_manager.register_raw_key("sk_test_exec_valid", name="exec_user", scopes={Scope.EXECUTE})
    api_key_manager.register_raw_key("sk_test_read_valid", name="read_user", scopes={Scope.READ})
    api_key_manager.register_raw_key("sk_test_revoked_key", name="revoked_user", scopes={Scope.ADMIN}, is_active=False)


def test_public_endpoints_accessible_without_auth(app_instance):
    """1. /health and /ready must remain public and accessible without credentials."""
    client = TestClient(app_instance)
    r1 = client.get("/health")
    assert r1.status_code == 200

    r2 = client.get("/ready")
    assert r2.status_code == 200


def test_protected_endpoints_missing_auth_returns_401(app_instance):
    """2. Calling protected endpoints without credentials returns 401 Unauthorized."""
    client = TestClient(app_instance)

    # Protected GET endpoints
    r1 = client.get("/api/v1/system/info")
    assert r1.status_code == 401
    assert "WWW-Authenticate" in r1.headers

    r2 = client.get("/api/v1/scenarios")
    assert r2.status_code == 401

    r3 = client.get("/api/v1/metrics")
    assert r3.status_code == 401

    # Protected POST endpoint
    r4 = client.post("/api/v1/scenarios/run", json={"scenario_name": "nominal_landing"})
    assert r4.status_code == 401


def test_protected_endpoints_invalid_or_revoked_auth_returns_401(app_instance):
    """3. Calling protected endpoints with invalid or revoked key returns 401."""
    client = TestClient(app_instance)

    # Invalid key
    r1 = client.get("/api/v1/system/info", headers={"Authorization": "Bearer sk_invalid_key_999"})
    assert r1.status_code == 401

    # Revoked key
    r2 = client.get("/api/v1/system/info", headers={"Authorization": "Bearer sk_test_revoked_key"})
    assert r2.status_code == 401

    # X-API-Key header with invalid key
    r3 = client.get("/api/v1/system/info", headers={"X-API-Key": "sk_bad_123"})
    assert r3.status_code == 401


def test_read_scope_access_and_forbidden_execution(app_instance):
    """4. Read-only key can access GET endpoints, but is 403 Forbidden on POST /scenarios/run."""
    client = TestClient(app_instance)
    headers = {"Authorization": "Bearer sk_test_read_valid"}

    # Allowed: Read endpoints
    r1 = client.get("/api/v1/system/info", headers=headers)
    assert r1.status_code == 200

    r2 = client.get("/api/v1/scenarios", headers=headers)
    assert r2.status_code == 200

    r3 = client.get("/api/v1/metrics", headers=headers)
    assert r3.status_code == 200

    # Denied: Execute endpoint requires Scope.EXECUTE
    r4 = client.post(
        "/api/v1/scenarios/run",
        json={"scenario_name": "nominal_landing", "seed": 42, "max_duration_sec": 1.0},
        headers=headers,
    )
    assert r4.status_code == 403
    data = r4.json()
    msg = data.get("message") or data.get("detail") or ""
    assert "Insufficient permissions" in msg


def test_execute_and_admin_scope_access(app_instance):
    """5. Execute and Admin keys can run simulation scenarios."""
    client = TestClient(app_instance)

    # Execute key
    r1 = client.post(
        "/api/v1/scenarios/run",
        json={"scenario_name": "nominal_landing", "seed": 42, "max_duration_sec": 1.0},
        headers={"Authorization": "Bearer sk_test_exec_valid"},
    )
    assert r1.status_code == 200

    # Admin key
    r2 = client.post(
        "/api/v1/scenarios/run",
        json={"scenario_name": "nominal_landing", "seed": 42, "max_duration_sec": 1.0},
        headers={"Authorization": "Bearer sk_test_admin_valid"},
    )
    assert r2.status_code == 200


def test_x_api_key_header_support(app_instance):
    """6. Authentication via X-API-Key header is fully supported."""
    client = TestClient(app_instance)
    response = client.get(
        "/api/v1/system/info",
        headers={"X-API-Key": "sk_test_read_valid"},
    )
    assert response.status_code == 200
    assert response.json()["application"] == "SkyVanta AI"
