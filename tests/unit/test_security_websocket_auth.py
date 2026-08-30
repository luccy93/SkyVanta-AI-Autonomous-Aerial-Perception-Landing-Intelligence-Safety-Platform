"""Unit tests for WebSocket handshake authentication and admission control."""

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
    api_key_manager.register_raw_key("sk_test_ws_valid", name="ws_user", scopes={Scope.READ})
    api_key_manager.register_raw_key("sk_test_ws_revoked", name="ws_revoked", scopes={Scope.READ}, is_active=False)


def test_websocket_missing_auth_rejected(app_instance):
    """1. WebSocket connection without authentication is rejected with policy violation (1008)."""
    client = TestClient(app_instance)
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/telemetry/ws") as ws:
            ws.receive_json()


def test_websocket_invalid_key_rejected(app_instance):
    """2. WebSocket connection with invalid key is rejected."""
    client = TestClient(app_instance)
    with pytest.raises(Exception):
        with client.websocket_connect(
            "/api/v1/telemetry/ws",
            headers={"Authorization": "Bearer sk_invalid_key_random"},
        ) as ws:
            ws.receive_json()


def test_websocket_revoked_key_rejected(app_instance):
    """3. WebSocket connection with revoked key is rejected."""
    client = TestClient(app_instance)
    with pytest.raises(Exception):
        with client.websocket_connect(
            "/api/v1/telemetry/ws",
            headers={"Authorization": "Bearer sk_test_ws_revoked"},
        ) as ws:
            ws.receive_json()


def test_websocket_bearer_header_authenticated_success(app_instance):
    """4. WebSocket connection with valid Bearer Authorization header streams successfully."""
    client = TestClient(app_instance)
    with client.websocket_connect(
        "/api/v1/telemetry/ws",
        headers={"Authorization": "Bearer sk_test_ws_valid"},
    ) as ws:
        packet = ws.receive_json()
        assert packet is not None
        assert "timestamp_sim_sec" in packet
        assert "landing_phase" in packet


def test_websocket_x_api_key_header_authenticated_success(app_instance):
    """5. WebSocket connection with valid X-API-Key header streams successfully."""
    client = TestClient(app_instance)
    with client.websocket_connect(
        "/api/v1/telemetry/ws",
        headers={"X-API-Key": "sk_test_ws_valid"},
    ) as ws:
        packet = ws.receive_json()
        assert packet is not None
        assert "position_m" in packet


def test_websocket_subprotocol_token_authenticated_success(app_instance):
    """6. WebSocket connection with Sec-WebSocket-Protocol token streams successfully."""
    client = TestClient(app_instance)
    with client.websocket_connect(
        "/api/v1/telemetry/ws",
        headers={"Sec-WebSocket-Protocol": "bearer.sk_test_ws_valid"},
    ) as ws:
        packet = ws.receive_json()
        assert packet is not None
        assert "velocity_m_s" in packet
