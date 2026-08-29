# SKYVANTA AI — REAL-TIME TELEMETRY WEBSOCKET
## PHASE D3 — REAL-TIME TELEMETRY STREAMING SPECIFICATION

**Document ID**: `SKYVANTA-D3-WEBSOCKET-TELEMETRY`  
**Date**: August 29, 2026  
**Status**: ACTIVE  
**Security Boundary**: SIMULATION-ONLY / HARDWARE-DISCONNECTED  

---

## 1. EXECUTIVE OVERVIEW

Phase D3 implements real-time asynchronous **WebSocket telemetry streaming** (`WS /api/v1/telemetry/ws`) exposing closed-loop 6-DoF digital twin simulation state to external dashboards, ground control stations, and monitoring tools.

Key guarantees:
- **Zero Physical Hardware**: Streamed telemetry originates exclusively from verified deterministic digital twin simulation models in software space.
- **Bounded Buffering & Backpressure**: Each subscriber connection maintains a bounded FIFO queue (`maxsize=50`); slow clients automatically drop stale packets without blocking producers or other clients.
- **Broadcaster Architecture**: A single simulation session efficiently broadcasts to multiple simultaneous WebSocket subscribers without redundant computation.
- **Clean Lifecycle & Heartbeat**: Explicit connection tracking, graceful client disconnection handling, application heartbeat (`ping`/`pong`), and server shutdown cleanup with zero orphaned background tasks.

---

## 2. WEBSOCKET ARCHITECTURE & DATA FLOW

```
   Client 1 (Dashboard)            Client 2 (Ground Control)
           │                                   │
           │ WS /api/v1/telemetry/ws           │ WS /api/v1/telemetry/ws
           ▼                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI WebSocket Endpoint                   │
│               (skyvanta.deployment.api.routes.telemetry)        │
│                                                                 │
│   ┌─────────────────────┐             ┌─────────────────────┐   │
│   │ Client 1 Sub Queue  │             │ Client 2 Sub Queue  │   │
│   │ (Bounded maxsize=50)│             │ (Bounded maxsize=50)│   │
│   └──────────▲──────────┘             └──────────▲──────────┘   │
└──────────────┼───────────────────────────────────┼──────────────┘
               │                                   │
               └───────── Broadcast Packet ────────┘
                                   ▲
                                   │ 20 Hz Ticks
┌──────────────────────────────────┴──────────────────────────────┐
│                    ScenarioBroadcastChannel                     │
│               (skyvanta.deployment.api.services)                │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │               TelemetrySimulationSession                │   │
│   │   • 6-DoF Vehicle Kinematics (SimulatedVehicle)         │   │
│   │   • Synthetic Vision & IMU (SimulatedCamera / IMU)      │   │
│   │   • 15-State Error-State EKF (ErrorStateExtendedKF)     │   │
│   │   • 12-State Landing FSM (LandingStateMachine)          │   │
│   │   • Safety Supervisor & Rate Limiter                    │   │
│   └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. PROTOCOL & CONNECTION SPECIFICATION

### 1. Connection Endpoint
- **URL**: `ws://<host>:<port>/api/v1/telemetry/ws`
- **Query Parameters**:
  - `scenario` *(optional, string)*: Target benchmark landing scenario name from the registry (e.g. `nominal_landing`, `target_loss`, `high_wind_landing`). Defaults to `nominal_landing`.
  - `rate_hz` *(optional, float)*: Target streaming frequency in Hertz. Defaults to `20.0` Hz.

### 2. Client Connection Example
```
ws://localhost:8080/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20.0
```

---

## 4. TELEMETRY PACKET SCHEMA

Streamed JSON packets are validated through `TelemetryStreamPacket` (`skyvanta/deployment/contracts.py`):

```json
{
  "packet_type": "telemetry",
  "scenario_name": "nominal_landing",
  "timestamp_sim_sec": 1.250,
  "position_m": [0.0842, -0.0415, 6.2104],
  "velocity_m_s": [0.0012, -0.0008, -0.4521],
  "attitude_rpy_deg": [0.42, -0.18, 12.50],
  "landing_phase": "DESCENDING",
  "recommended_action": "CONTINUE_DESCENT",
  "target_visible": true,
  "position_uncertainty_3sigma_m": 0.0428,
  "is_safe": true
}
```

### Schema Field Definitions

| Field Name | Type | Description |
|---|---|---|
| `packet_type` | `string` | Packet identifier (`"telemetry"`). |
| `scenario_name` | `string` | Name of the active digital twin scenario. |
| `timestamp_sim_sec` | `float` | Simulated mission elapsed time in seconds. |
| `position_m` | `List[float]` | Estimated 3D vehicle position $[x, y, z]$ in meters (ENU). |
| `velocity_m_s` | `List[float]` | Estimated 3D velocity $[v_x, v_y, v_z]$ in m/s. |
| `attitude_rpy_deg` | `List[float]` | Orientation $[\text{roll}, \text{pitch}, \text{yaw}]$ in degrees. |
| `landing_phase` | `string` | Active landing FSM operational phase. |
| `recommended_action` | `string` | Supervisor recommended flight guidance action. |
| `target_visible` | `boolean` | True if the landing target is actively tracked. |
| `position_uncertainty_3sigma_m` | `float` | ESEKF 3-sigma position covariance boundary. |
| `is_safe` | `boolean` | Hard multi-invariant safety compliance boolean. |

---

## 5. HEARTBEAT & ERROR PROTOCOL

### 1. Application Heartbeat
Clients may send a `"ping"` string or `{"type": "ping"}` JSON frame at any time. The server responds immediately:
```json
{
  "type": "pong",
  "timestamp_sec": 1788005400.1234,
  "connection_id": "ws_a1b2c3d4"
}
```

### 2. Error Response Structure
If an invalid scenario is requested or an unrecoverable condition occurs:
```json
{
  "type": "error",
  "code": "SCENARIO_NOT_FOUND",
  "message": "Benchmark scenario 'unknown_scenario' not found in registry.",
  "connection_id": "ws_a1b2c3d4"
}
```

---

## 6. MULTI-CLIENT & BACKPRESSURE SPECIFICATION

1. **Independent Subscriber Queues**: Each WebSocket connection receives its own `asyncio.Queue(maxsize=50)`.
2. **Oldest-Drop Policy**: If a client falls behind (e.g. network latency or UI hang), the broadcast engine discards the oldest pending packet (`get_nowait()`) and enqueues the latest frame. Server memory is strictly bounded ($O(1)$ per connection).
3. **No Cross-Client Blocking**: A slow client never delays telemetry delivery to concurrent fast clients.
4. **Lifecycle Cleanup**: When all subscribers unsubscribe, the simulation broadcast task is stopped automatically.

---

## 7. LOCAL TESTING & VERIFICATION

### 1. Python WebSocket Client
```python
import asyncio
import websockets
import json

async def receive_telemetry():
    uri = "ws://localhost:8080/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20"
    async with websockets.connect(uri) as websocket:
        while True:
            msg = await websocket.recv()
            data = json.loads(msg)
            print(f"t={data['timestamp_sim_sec']}s | Phase: {data['landing_phase']} | Pos: {data['position_m']}")

asyncio.run(receive_telemetry())
```

### 2. Run Test Suite
```bash
pytest tests/unit/test_telemetry_websocket.py -v
```

---

## 8. SECURITY & ISOLATION GUARANTEES

- **Simulation-Only Operation**: Operates purely in software memory without connecting to physical serial, MAVLink, PX4, or ArduPilot interfaces.
- **Hardware Isolation**: `allow_external: false`, `hardware_disconnected: true`.
- **Zero Runtime Downloads**: `allow_network_download: false`.
