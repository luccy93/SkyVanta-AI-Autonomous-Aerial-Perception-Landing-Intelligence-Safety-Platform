"""Real-time telemetry WebSocket streaming route."""

import asyncio
import json
import logging
import time
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status

from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.api.dependencies import (
    get_deployment_config_ws,
    get_telemetry_service_ws,
)
from skyvanta.deployment.api.services.telemetry_service import TelemetryService
from skyvanta.simulation.registry import ScenarioRegistry

logger = logging.getLogger("skyvanta.api.telemetry")

router = APIRouter(prefix="/api/v1/telemetry", tags=["Telemetry"])


@router.websocket("/ws")
async def telemetry_websocket_endpoint(
    websocket: WebSocket,
    scenario: Optional[str] = Query(
        default=None,
        description="Benchmark scenario name to stream (default: nominal_landing)",
    ),
    rate_hz: Optional[float] = Query(
        default=None,
        description="Requested streaming frequency in Hz (default: 20.0)",
    ),
    config: DeploymentConfig = Depends(get_deployment_config_ws),
    telemetry_service: TelemetryService = Depends(get_telemetry_service_ws),
) -> None:
    """Streams real-time 6-DoF digital twin telemetry packets over WebSocket."""
    from skyvanta.deployment.observability.events import EventType, event_logger
    from skyvanta.deployment.observability.metrics import metrics_collector
    from skyvanta.deployment.security import authenticate_websocket, Scope

    # 0. Secure Handshake Authentication
    if config.enable_auth:
        key_record = await authenticate_websocket(websocket, required_scope=Scope.READ)
        if key_record is None:
            # Rejection and WS_1008 closure handled inside authenticate_websocket
            return

    await websocket.accept()
    conn_id = f"ws_{uuid4().hex[:8]}"
    t_conn_start = time.monotonic()

    scenario_name = scenario.strip() if (scenario and scenario.strip()) else "nominal_landing"
    logger.info("WebSocket connected [ID: %s, Scenario: %s]", conn_id, scenario_name)

    # 1. Enforce maximum simultaneous WebSocket client connections
    if len(telemetry_service._active_connections) >= config.max_ws_clients:
        logger.warning(
            "WebSocket rejected [ID: %s]: Max client connections (%d) reached.",
            conn_id,
            config.max_ws_clients,
        )
        metrics_collector.record_error("websocket")
        await websocket.send_json({
            "type": "error",
            "code": "MAX_CLIENTS_EXCEEDED",
            "message": f"Server connection limit ({config.max_ws_clients}) reached.",
            "connection_id": conn_id,
        })
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Validate scenario exists in registered benchmark catalog
    if ScenarioRegistry.get(scenario_name) is None:
        logger.warning(
            "WebSocket rejected [ID: %s]: Scenario '%s' not found.",
            conn_id,
            scenario_name,
        )
        metrics_collector.record_error("websocket")
        await websocket.send_json({
            "type": "error",
            "code": "SCENARIO_NOT_FOUND",
            "message": f"Benchmark scenario '{scenario_name}' not found in registry.",
            "connection_id": conn_id,
        })
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 3. Configure streaming rate & record connection
    stream_rate_hz = rate_hz if (rate_hz is not None and rate_hz > 0) else config.telemetry_rate_hz
    metrics_collector.set_ws_configured_rate(stream_rate_hz)
    metrics_collector.record_ws_connect()

    event_logger.emit(
        event_type=EventType.WEBSOCKET_CONNECTED,
        message=f"WebSocket client connected [ID: {conn_id}, Scenario: {scenario_name}]",
        severity="INFO",
        details={
            "connection_id": conn_id,
            "scenario_name": scenario_name,
            "stream_rate_hz": stream_rate_hz,
            "active_connections": metrics_collector.ws_active_connections,
        },
        environment=config.environment.value,
    )

    # 4. Obtain broadcast channel & subscribe client queue
    channel = await telemetry_service.get_or_create_channel(
        scenario_name=scenario_name,
        rate_hz=stream_rate_hz,
    )
    client_queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    channel.subscribe(client_queue)
    telemetry_service.register_connection(websocket)

    # 5. Asynchronous Send and Receive loops
    async def send_loop():
        try:
            while True:
                packet = await client_queue.get()
                if packet is None:
                    await websocket.send_json({
                        "type": "stream_completed",
                        "scenario_name": scenario_name,
                        "connection_id": conn_id,
                    })
                    break
                await websocket.send_json(packet.model_dump())
        except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
            pass

    async def receive_loop():
        try:
            while True:
                raw_text = await websocket.receive_text()
                try:
                    payload = json.loads(raw_text)
                    if isinstance(payload, dict):
                        msg_type = str(payload.get("type", "")).lower()
                        if msg_type == "ping":
                            await websocket.send_json({
                                "type": "pong",
                                "timestamp_sec": round(time.time(), 4),
                                "connection_id": conn_id,
                            })
                        elif msg_type == "close":
                            break
                        else:
                            metrics_collector.record_error("websocket")
                            await websocket.send_json({
                                "type": "error",
                                "code": "UNSUPPORTED_MESSAGE",
                                "message": f"Unrecognized message type '{msg_type}'.",
                                "connection_id": conn_id,
                            })
                    else:
                        metrics_collector.record_error("websocket")
                        metrics_collector.record_ws_heartbeat_failure()
                        await websocket.send_json({
                            "type": "error",
                            "code": "INVALID_FORMAT",
                            "message": "Message body must be a valid JSON object.",
                            "connection_id": conn_id,
                        })
                except json.JSONDecodeError:
                    if raw_text.strip().lower() == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp_sec": round(time.time(), 4),
                            "connection_id": conn_id,
                        })
                    else:
                        metrics_collector.record_error("websocket")
                        metrics_collector.record_ws_heartbeat_failure()
                        event_logger.emit(
                            event_type=EventType.HEARTBEAT_FAILURE,
                            message=f"Malformed WebSocket message from {conn_id}",
                            severity="WARNING",
                            details={"connection_id": conn_id},
                            environment=config.environment.value,
                        )
                        await websocket.send_json({
                            "type": "error",
                            "code": "MALFORMED_MESSAGE",
                            "message": "Message payload could not be parsed as JSON.",
                            "connection_id": conn_id,
                        })
        except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
            pass

    send_task = asyncio.create_task(send_loop())
    recv_task = asyncio.create_task(receive_loop())

    try:
        _, pending = await asyncio.wait(
            [send_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
    finally:
        channel.unsubscribe(client_queue)
        telemetry_service.unregister_connection(websocket)
        conn_duration = max(0.0, time.monotonic() - t_conn_start)
        metrics_collector.record_ws_disconnect(round(conn_duration, 3))

        event_logger.emit(
            event_type=EventType.WEBSOCKET_DISCONNECTED,
            message=f"WebSocket client disconnected [ID: {conn_id}, Duration: {round(conn_duration, 2)}s]",
            severity="INFO",
            details={
                "connection_id": conn_id,
                "scenario_name": scenario_name,
                "duration_sec": round(conn_duration, 2),
                "active_connections": metrics_collector.ws_active_connections,
            },
            environment=config.environment.value,
        )
        logger.info("WebSocket disconnected [ID: %s, Scenario: %s, Duration: %.2fs]", conn_id, scenario_name, conn_duration)
        try:
            await websocket.close()
        except Exception:
            pass
