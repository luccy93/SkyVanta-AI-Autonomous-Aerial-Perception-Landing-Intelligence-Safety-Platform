"""Unit tests for the real-time telemetry WebSocket streaming endpoint."""

import asyncio
import time
import pytest
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.contracts import TelemetryStreamPacket
from skyvanta.deployment.api.services.telemetry_service import (
    ScenarioBroadcastChannel,
    TelemetrySimulationSession,
)
from skyvanta.simulation.registry import ScenarioRegistry


@pytest.fixture
def client():
    """Provides a TestClient connected to a testing configured FastAPI app instance."""
    app = create_app(
        DeploymentConfig(
            environment=DeploymentEnvironment.TESTING,
            telemetry_rate_hz=50.0,
        )
    )
    return TestClient(app)


def test_websocket_connection_default_scenario(client):
    """1. WebSocket connects and streams telemetry from default scenario."""
    with client.websocket_connect("/api/v1/telemetry/ws") as ws:
        packet_data = ws.receive_json()
        assert packet_data is not None
        assert "timestamp_sim_sec" in packet_data
        assert "position_m" in packet_data
        assert "velocity_m_s" in packet_data
        assert "landing_phase" in packet_data
        assert "recommended_action" in packet_data


def test_websocket_connection_valid_scenario(client):
    """2. Client connects with specific valid scenario parameter."""
    with client.websocket_connect("/api/v1/telemetry/ws?scenario=target_loss") as ws:
        packet_data = ws.receive_json()
        assert packet_data["scenario_name"] == "target_loss"
        assert packet_data["timestamp_sim_sec"] >= 0.0


def test_websocket_connection_invalid_scenario_returns_error(client):
    """3. Connecting to a non-existent scenario returns structured error and closes."""
    with client.websocket_connect("/api/v1/telemetry/ws?scenario=unknown_invalid_scn") as ws:
        response = ws.receive_json()
        assert response["type"] == "error"
        assert response["code"] == "SCENARIO_NOT_FOUND"
        assert "unknown_invalid_scn" in response["message"]
        assert "connection_id" in response


def test_telemetry_packet_schema_validation(client):
    """4. Streamed packets conform to TelemetryStreamPacket Pydantic schema."""
    with client.websocket_connect("/api/v1/telemetry/ws?scenario=nominal_landing") as ws:
        for _ in range(3):
            data = ws.receive_json()
            packet = TelemetryStreamPacket(**data)
            assert len(packet.position_m) == 3
            assert len(packet.velocity_m_s) == 3
            assert len(packet.attitude_rpy_deg) == 3
            assert isinstance(packet.target_visible, bool)
            assert isinstance(packet.is_safe, bool)
            assert packet.position_uncertainty_3sigma_m >= 0.0


def test_telemetry_stream_rate_configuration(client):
    """5. Stream rate parameter configures transmission interval."""
    with client.websocket_connect("/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=100") as ws:
        t_start = time.perf_counter()
        p1 = ws.receive_json()
        p2 = ws.receive_json()
        dt_wall = time.perf_counter() - t_start
        assert p2["timestamp_sim_sec"] >= p1["timestamp_sim_sec"]
        assert dt_wall < 1.0


def test_websocket_clean_client_disconnect(client):
    """6. Client disconnecting abruptly or normally cleans up cleanly without server error."""
    with client.websocket_connect("/api/v1/telemetry/ws") as ws:
        _ = ws.receive_json()
        ws.close()


def test_websocket_heartbeat_and_malformed_messages(client):
    """7. Server responds to ping heartbeat and handles malformed payloads gracefully."""
    with client.websocket_connect("/api/v1/telemetry/ws") as ws:
        # Drain initial packet
        _ = ws.receive_json()

        # Send text 'ping'
        ws.send_text("ping")
        resp = ws.receive_json()
        for _ in range(5):
            if resp.get("type") == "pong":
                break
            resp = ws.receive_json()
        assert resp.get("type") == "pong"
        assert "timestamp_sec" in resp

        # Send JSON ping
        ws.send_json({"type": "ping"})
        resp2 = ws.receive_json()
        for _ in range(5):
            if resp2.get("type") == "pong":
                break
            resp2 = ws.receive_json()
        assert resp2.get("type") == "pong"

        # Send malformed JSON text
        ws.send_text("THIS_IS_NOT_VALID_JSON{")
        resp3 = ws.receive_json()
        for _ in range(5):
            if resp3.get("type") == "error":
                break
            resp3 = ws.receive_json()
        assert resp3.get("type") == "error"
        assert resp3.get("code") == "MALFORMED_MESSAGE"


def test_simulation_step_generation():
    """8. TelemetrySimulationSession steps through scenario producing realistic telemetry."""
    scenario = ScenarioRegistry.get("nominal_landing")
    assert scenario is not None
    session = TelemetrySimulationSession(scenario, rate_hz=20.0)

    packets = []
    for _ in range(10):
        pkt = session.step()
        if pkt is not None:
            packets.append(pkt)

    assert len(packets) == 10
    assert packets[0].timestamp_sim_sec == 0.0
    assert packets[-1].timestamp_sim_sec > packets[0].timestamp_sim_sec
    assert packets[0].landing_phase in ("SEARCHING", "TARGET_ACQUIRED", "ALIGNING")


@pytest.mark.asyncio
async def test_multiple_subscribers_broadcast():
    """9. Broadcaster streams to multiple independent client queues simultaneously without interference."""
    scenario = ScenarioRegistry.get("nominal_landing")
    assert scenario is not None
    channel = ScenarioBroadcastChannel(scenario, rate_hz=50.0)

    q1: asyncio.Queue = asyncio.Queue(maxsize=10)
    q2: asyncio.Queue = asyncio.Queue(maxsize=10)

    channel.subscribe(q1)
    channel.subscribe(q2)

    await asyncio.sleep(0.08)

    assert not q1.empty()
    assert not q2.empty()

    p1 = await q1.get()
    p2 = await q2.get()

    assert p1 is not None
    assert p2 is not None
    assert p1.timestamp_sim_sec == p2.timestamp_sim_sec

    channel.unsubscribe(q1)
    channel.unsubscribe(q2)


def test_bounded_buffering_and_backpressure():
    """10. Slow subscriber queues drop oldest stale packets and maintain bounded size."""
    scenario = ScenarioRegistry.get("nominal_landing")
    assert scenario is not None
    channel = ScenarioBroadcastChannel(scenario, rate_hz=20.0)

    slow_queue: asyncio.Queue = asyncio.Queue(maxsize=3)
    channel.subscribers.add(slow_queue)

    pkt1 = TelemetryStreamPacket(
        timestamp_sim_sec=0.1,
        position_m=[0.0, 0.0, 10.0],
        velocity_m_s=[0.0, 0.0, 0.0],
        attitude_rpy_deg=[0.0, 0.0, 0.0],
        landing_phase="SEARCHING",
        recommended_action="HOVER",
        target_visible=True,
        position_uncertainty_3sigma_m=0.05,
        is_safe=True,
    )
    pkt2 = pkt1.model_copy(update={"timestamp_sim_sec": 0.2})
    pkt3 = pkt1.model_copy(update={"timestamp_sim_sec": 0.3})
    pkt4 = pkt1.model_copy(update={"timestamp_sim_sec": 0.4})

    channel.broadcast(pkt1)
    channel.broadcast(pkt2)
    channel.broadcast(pkt3)
    # Queue is now full (3 items). Broadcasting 4th item should drop pkt1 and keep pkt4
    channel.broadcast(pkt4)

    assert slow_queue.qsize() == 3
    received_items = []
    while not slow_queue.empty():
        received_items.append(slow_queue.get_nowait())

    # pkt1 should have been dropped; pkt2, pkt3, pkt4 remain
    assert received_items[0].timestamp_sim_sec == 0.2
    assert received_items[1].timestamp_sim_sec == 0.3
    assert received_items[2].timestamp_sim_sec == 0.4


@pytest.mark.asyncio
async def test_shutdown_cleanup():
    """11. TelemetryService shutdown stops all broadcast channels and clears state."""
    app = create_app(DeploymentConfig(environment=DeploymentEnvironment.TESTING))
    telemetry_service = app.state.telemetry_service

    channel = await telemetry_service.get_or_create_channel("nominal_landing")
    q: asyncio.Queue = asyncio.Queue(maxsize=5)
    channel.subscribe(q)
    assert len(telemetry_service._channels) >= 1

    await telemetry_service.shutdown()
    assert len(telemetry_service._channels) == 0
    assert len(telemetry_service._active_connections) == 0


def test_hardware_isolation_invariants():
    """12. Telemetry service verifies zero physical hardware access invariants."""
    config = DeploymentConfig.from_env()
    assert config.allow_external is False
    assert config.hardware_disconnected is True


def test_network_download_isolation_invariants():
    """13. Telemetry service verifies zero runtime network model downloads."""
    config = DeploymentConfig.from_env()
    assert config.allow_network_download is False
