# SkyVanta AI — Production API Reference & Showcase

**Document ID**: `SKYVANTA-D11.5-API-REFERENCE`  
**Base URL (Local)**: `http://localhost:8080`  
**Base URL (Cloud)**: `https://skyvanta-ai.onrender.com`  
**Interactive Docs**: `https://skyvanta-ai.onrender.com/docs` (Swagger UI) / `https://skyvanta-ai.onrender.com/redoc` (ReDoc)  
**Security Model**: Role-Based Access Control (RBAC) • SHA-256 Key Hashing • Tiered Token-Bucket Rate Limiting  
**Operational Mode**: Software-in-the-Loop (SIL) • Hardware Disconnected (`hardware_access: false`)  

---

## 1. Authentication & Security Model

SkyVanta AI enforces fine-grained role-based access control (RBAC) across all protected API routes and WebSocket connections.

### 1.1 API Key Transmission Methods
Protected endpoints accept API keys via three standard channels:

1. **HTTP Authorization Header** (Standard Bearer Token):
   ```http
   Authorization: Bearer sk_test_admin_key_12345
   ```
2. **Custom HTTP Header**:
   ```http
   X-API-Key: sk_test_admin_key_12345
   ```
3. **WebSocket Subprotocol Header** (`Sec-WebSocket-Protocol`):
   ```http
   Sec-WebSocket-Protocol: bearer.sk_test_admin_key_12345
   ```

### 1.2 Authorization Scopes Hierarchy
Permissions are structured into three hierarchical scopes. Higher privileges automatically satisfy lower permission requirements:

```text
┌────────────────────────────────────────────────────────┐
│                      Scope.ADMIN                       │
│           (Full Configuration & Diagnostics)           │
├────────────────────────────────────────────────────────┤
│                     Scope.EXECUTE                      │
│             (6-DoF Digital Twin Simulation)            │
├────────────────────────────────────────────────────────┤
│                       Scope.READ                       │
│         (Telemetry, Metrics, Catalog, Release)         │
└────────────────────────────────────────────────────────┘
```

| Scope Identifier | Key Name Pattern | Permitted Operations |
| :--- | :--- | :--- |
| **`Scope.READ`** | `sk_read_*` | Read system info, list scenarios, inspect release manifest, stream WebSocket telemetry, fetch observability metrics. |
| **`Scope.EXECUTE`** | `sk_exec_*` | All `READ` operations + trigger closed-loop 6-DoF digital twin scenario runs (`POST /api/v1/scenarios/run`). |
| **`Scope.ADMIN`** | `sk_admin_*` | All `EXECUTE` & `READ` operations + administrative diagnostics and audit log inspection. |

### 1.3 Security Implementation Details
* **Constant-Time Verification**: Secret keys are hashed with SHA-256 and compared using `hmac.compare_digest` to prevent timing attacks.
* **Payload Size Protection**: Request bodies are capped at **64 KB**; larger payloads return `413 Payload Too Large`.
* **Zero Unsafe Primitives**: The codebase contains zero dynamic evaluation primitives (`eval`, `exec`, `pickle`, `os.system`).

---

## 2. Rate Limiting Policy

Endpoints are protected by a thread-safe **Tiered Token-Bucket Rate Limiter** with bounded memory:

| Rate Limit Tier | Associated Endpoints | Sustained Rate | Burst Capacity | Violation Response |
| :--- | :--- | :---: | :---: | :--- |
| **`READ`** | `/api/v1/scenarios`, `/api/v1/system/info`, `/api/v1/release` | 120 req/min | 30 tokens | `429 Too Many Requests` + `Retry-After` header |
| **`EXECUTE`** | `/api/v1/scenarios/run` | 30 req/min | 10 tokens | `429 Too Many Requests` + `Retry-After` header |
| **`METRICS`** | `/api/v1/metrics` | 60 req/min | 20 tokens | `429 Too Many Requests` + `Retry-After` header |

---

## 3. REST API Endpoint Reference

---

### 3.1 Infrastructure Health Check

* **METHOD**: `GET`
* **PATH**: `/health`
* **Authentication**: None (Public)
* **Purpose**: Infrastructure liveness probe and immediate safety boundary audit. Used by load balancers and orchestrators.
* **Request**:
  - Headers: None required
  - Parameters: None
* **Response Contract** (`DeploymentHealthContract`):
  ```json
  {
    "status": "healthy",
    "service": "skyvanta-api",
    "version": "0.1.0",
    "environment": "development",
    "uptime_sec": 1231.74,
    "simulation_engine": "ready",
    "available_scenarios_count": 12,
    "hardware_access": false,
    "network_model_download": false,
    "safety_boundary_enforced": true,
    "timestamp_sec": 1788250884.552
  }
  ```
* **Example Command**:
  ```bash
  curl -s http://localhost:8080/health
  ```
* **Expected Status Codes**: `200 OK` (Healthy), `503 Service Unavailable` (Unhealthy).
* **Safety Considerations**: Confirms `hardware_access` is strictly `false` and safety invariants are actively enforced.

---

### 3.2 Operational Readiness Probe

* **METHOD**: `GET`
* **PATH**: `/ready`
* **Authentication**: None (Public)
* **Purpose**: Verifies operational dependencies (scenario catalog loaded, simulation engine initialized, safety locks engaged) before admitting traffic.
* **Request**:
  - Headers: None required
  - Parameters: None
* **Response Contract** (`DeploymentReadinessContract`):
  ```json
  {
    "ready": true,
    "status": "ready",
    "service": "skyvanta-api",
    "version": "0.1.0",
    "environment": "development",
    "checks": {
      "scenario_catalog_loaded": true,
      "simulation_engine_ready": true,
      "safety_invariants_enforced": true
    },
    "uptime_sec": 1232.27,
    "timestamp_sec": 1788250884.555
  }
  ```
* **Example Command**:
  ```bash
  curl -s http://localhost:8080/ready
  ```
* **Expected Status Codes**: `200 OK` (Ready), `503 Service Unavailable` (Dependency check failed).

---

### 3.3 System Information & Capabilities

* **METHOD**: `GET`
* **PATH**: `/api/v1/system/info`
* **Authentication**: Required (`Scope.READ`)
* **Purpose**: Discloses runtime environment, Git commit identifier, and active algorithmic capabilities.
* **Request**:
  - Headers: `Authorization: Bearer <API_KEY>` or `X-API-Key: <API_KEY>`
* **Response Contract** (`SystemInfoResponse`):
  ```json
  {
    "application": "SkyVanta AI",
    "version": "0.1.0",
    "api_version": "v1",
    "environment": "development",
    "git_commit": "803e36bc7bc6124462cfda6b504af5449da95bb3",
    "build_timestamp": "2026-08-30T00:00:00Z",
    "hardware_access": false,
    "network_model_download": false,
    "safety_boundary_enforced": true,
    "supported_capabilities": [
      "6_dof_digital_twin_simulation",
      "15_state_esekf_sensor_fusion",
      "monocular_6dof_pnp_localization",
      "multi_target_kf_tracking",
      "12_state_safety_fsm_supervision",
      "rate_limited_flight_command_authorization",
      "deterministic_scenario_replay",
      "monte_carlo_batch_validation"
    ]
  }
  ```
* **Example Command**:
  ```bash
  curl -s -H "Authorization: Bearer sk_test_admin_key_12345" \
    http://localhost:8080/api/v1/system/info
  ```
* **Expected Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`.

---

### 3.4 List Benchmark Scenarios

* **METHOD**: `GET`
* **PATH**: `/api/v1/scenarios`
* **Authentication**: Required (`Scope.READ`)
* **Purpose**: Returns the catalog of 12 registered digital twin landing benchmark scenarios.
* **Request**:
  - Headers: `Authorization: Bearer <API_KEY>`
* **Response Contract** (`List[ScenarioCatalogItem]`):
  ```json
  [
    {
      "scenario_id": "SCN_NOMINAL_01",
      "name": "nominal_landing",
      "description": "Calm nominal vertical descent from 8m to safe touchdown on stationary pad",
      "duration_sec": 20.0,
      "timestep_sec": 0.05,
      "seed": 42,
      "expected_outcome": "SUCCESS_LANDED",
      "events_count": 0
    },
    {
      "scenario_id": "SCN_TARGET_LOSS_02",
      "name": "target_loss",
      "description": "Complete visual target loss for 2.5s during descent; requires immediate abort",
      "duration_sec": 15.0,
      "timestep_sec": 0.05,
      "seed": 42,
      "expected_outcome": "SUCCESS_ABORTED",
      "events_count": 1
    }
  ]
  ```
* **Example Command**:
  ```bash
  curl -s -H "Authorization: Bearer sk_test_admin_key_12345" \
    http://localhost:8080/api/v1/scenarios
  ```
* **Expected Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`.

---

### 3.5 Get Scenario Details

* **METHOD**: `GET`
* **PATH**: `/api/v1/scenarios/{scenario_name}`
* **Authentication**: Required (`Scope.READ`)
* **Purpose**: Retrieves full kinematic starting state, duration, and dynamic perturbation events for a specific scenario.
* **Path Parameter**: `scenario_name` (e.g. `nominal_landing`, `target_loss`, `high_winds`)
* **Response Contract** (`ScenarioDetailItem`):
  ```json
  {
    "scenario_id": "SCN_NOMINAL_01",
    "name": "nominal_landing",
    "description": "Calm nominal vertical descent from 8m to safe touchdown on stationary pad",
    "duration_sec": 20.0,
    "timestep_sec": 0.05,
    "seed": 42,
    "expected_outcome": "SUCCESS_LANDED",
    "events_count": 0,
    "initial_vehicle_pos": [0.1, 0.1, 8.0],
    "initial_vehicle_vel": [0.0, 0.0, 0.0],
    "initial_vehicle_euler_deg": [0.0, 0.0, 0.0],
    "events": []
  }
  ```
* **Example Command**:
  ```bash
  curl -s -H "Authorization: Bearer sk_test_admin_key_12345" \
    http://localhost:8080/api/v1/scenarios/nominal_landing
  ```
* **Expected Status Codes**: `200 OK`, `404 Not Found`, `401 Unauthorized`.

---

### 3.6 Execute Simulation Scenario

* **METHOD**: `POST`
* **PATH**: `/api/v1/scenarios/run`
* **Authentication**: Required (`Scope.EXECUTE`)
* **Purpose**: Runs a closed-loop 6-DoF digital twin simulation run and returns quantitative estimation metrics and safety audit results.
* **Request Schema** (`ScenarioRunRequest`):
  ```json
  {
    "scenario_name": "nominal_landing",
    "seed": 42,
    "record_telemetry": false
  }
  ```
* **Response Contract** (`ScenarioRunResponse`):
  ```json
  {
    "run_id": "api_run_nominal_landing_42_37c514d7aaef44818bcb5ec6ff28c111",
    "scenario_name": "SCN_NOMINAL_01",
    "status": "SUCCESS_LANDED",
    "seed": 42,
    "duration_sim_sec": 15.85,
    "duration_wall_sec": 0.20,
    "realtime_factor": 79.29,
    "final_position_error_m": 0.0,
    "rmse_position_m": 0.0143,
    "safety_violations_count": 0,
    "is_success": true,
    "error_message": null
  }
  ```
* **Example Command**:
  ```bash
  curl -s -X POST \
    -H "Authorization: Bearer sk_test_admin_key_12345" \
    -H "Content-Type: application/json" \
    -d '{"scenario_name": "nominal_landing", "seed": 42}' \
    http://localhost:8080/api/v1/scenarios/run
  ```
* **Expected Status Codes**: `200 OK`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `429 Rate Limit Exceeded`.
* **Safety Considerations**: Execution is strictly confined to the in-memory digital twin physics engine. Actuator commands are routed exclusively to internal simulation state variables.

---

### 3.7 Release Metadata & Verification Status

* **METHOD**: `GET`
* **PATH**: `/api/v1/release`
* **Authentication**: Required (`Scope.READ`)
* **Purpose**: Inspects release manifest, Git commit integrity, and verifies that safety boundaries are intact.
* **Response Contract** (`ReleaseResponse`):
  ```json
  {
    "application": "SkyVanta AI",
    "version": "0.1.0",
    "api_version": "v1",
    "git_commit": "803e36bc7bc6124462cfda6b504af5449da95bb3",
    "environment": "development",
    "core_version": "V1-V9",
    "hardware_access": false,
    "network_model_download": false,
    "release_verified": true
  }
  ```
* **Example Command**:
  ```bash
  curl -s -H "Authorization: Bearer sk_test_admin_key_12345" \
    http://localhost:8080/api/v1/release
  ```
* **Expected Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`.

---

### 3.8 Operational Observability Metrics

* **METHOD**: `GET`
* **PATH**: `/api/v1/metrics`
* **Authentication**: Required (`Scope.READ`)
* **Purpose**: Returns real-time latency percentiles (min, avg, p50, p95, p99, max), HTTP throughput counters, active WebSocket client stats, and memory RSS utilization.
* **Response Contract** (`MetricsResponseContract`):
  ```json
  {
    "service": "skyvanta-api",
    "version": "0.1.0",
    "environment": "development",
    "timestamp_sec": 1788250884.965,
    "http": {
      "total_requests": 24,
      "successful_requests": 23,
      "failed_requests": 1,
      "requests_by_endpoint": {
        "/health": 4,
        "/ready": 3,
        "/api/v1/scenarios/run": 4,
        "/api/v1/metrics": 2
      }
    },
    "latencies_ms": {
      "/health": { "p50": 5.62, "p95": 8.14, "p99": 21.67 },
      "/api/v1/scenarios/run": { "p50": 199.9, "p95": 359.8, "p99": 380.1 }
    },
    "system": {
      "memory_rss_mb": 88.38,
      "cpu_usage_pct": 2.1
    },
    "warnings": []
  }
  ```
* **Example Command**:
  ```bash
  curl -s -H "Authorization: Bearer sk_test_admin_key_12345" \
    http://localhost:8080/api/v1/metrics
  ```
* **Expected Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`, `429 Rate Limit Exceeded`.

---

## 4. Real-Time Telemetry WebSocket API

SkyVanta AI delivers low-latency 6-DoF vehicle and filter state streaming via persistent WebSocket connections.

### 4.1 Connection URL & Parameters
```text
ws://localhost:8080/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20
```
or over secure TLS in production:
```text
wss://skyvanta-ai.onrender.com/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20
```

| Parameter | Type | Required | Default | Description | Bounds |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `scenario` | `string` | No | `nominal_landing` | Benchmark scenario name to simulate and broadcast | Must exist in scenario registry |
| `rate_hz` | `float` | No | `20.0` | Target telemetry streaming broadcast frequency | $1.0\text{ Hz} \le \text{rate\_hz} \le 50.0\text{ Hz}$ |

### 4.2 WebSocket Authentication
Authentication is verified during the WebSocket handshake before connection admission:
- **Option A**: Standard `Authorization: Bearer <API_KEY>` HTTP header during initial upgrade request.
- **Option B**: `X-API-Key: <API_KEY>` HTTP header.
- **Option C**: Subprotocol parameter: `Sec-WebSocket-Protocol: bearer.<API_KEY>`.

If authentication is missing or invalid, the server rejects the handshake with **`HTTP 403 Forbidden`** or terminates with WebSocket code **`1008 Policy Violation`**.

### 4.3 Telemetry Packet Schema
Each packet is transmitted as a JSON object adhering to the verified internal contract:

```json
{
  "packet_type": "telemetry",
  "scenario_name": "nominal_landing",
  "timestamp_sim_sec": 0.05,
  "position_m": [ 0.1091, 0.0982, 8.0018 ],
  "velocity_m_s": [ 0.0030, -0.0054, -0.0030 ],
  "attitude_rpy_deg": [ 0.0, -0.0, 0.0 ],
  "landing_phase": "ALIGNING",
  "recommended_action": "ALIGN",
  "target_visible": true,
  "position_uncertainty_3sigma_m": 0.3681,
  "is_safe": true
}
```

### 4.4 Heartbeat & Connection Lifecycle
* **Client Keepalive**: Clients may transmit `ping` text frames; the server responds immediately with `{"type": "pong", "timestamp": ...}`.
* **Backpressure Management**: Each client is allocated an isolated bounded queue (`maxsize=50`). If a client consumes frames slower than the simulation broadcast rate, stale frames are dropped without impacting server performance or other subscribers.
* **Clean Disconnection**: Normal termination is handled via `1000 Normal Closure`. Abnormal drops are logged and resources released within $1\text{ ms}$.

### 4.5 Python WebSocket Client Example
```python
import asyncio
import json
import websockets

async def stream_telemetry():
    uri = "ws://localhost:8080/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20"
    headers = {"Authorization": "Bearer sk_test_admin_key_12345"}
    
    async with websockets.connect(uri, additional_headers=headers) as ws:
        print("Connected to SkyVanta AI Telemetry Stream...")
        while True:
            raw_msg = await ws.recv()
            packet = json.loads(raw_msg)
            print(f"[{packet['timestamp_sim_sec']:.2f}s] Phase: {packet['landing_phase']} | "
                  f"Pos: {packet['position_m']} | Uncertainty 3σ: {packet['position_uncertainty_3sigma_m']:.3f}m")

if __name__ == "__main__":
    asyncio.run(stream_telemetry())
```

---

## 5. Standard Error Responses

All API errors return consistent JSON payloads with correlation tracking IDs:

```json
{
  "error_code": "RESOURCE_NOT_FOUND",
  "message": "Benchmark scenario 'unknown_scenario' not found in registry.",
  "request_id": "req_84f91e028b1a",
  "timestamp_sec": 1788250885.120
}
```

### Standard Status Codes
* **`200 OK`**: Request processed successfully.
* **`400 Bad Request`**: Malformed payload or validation error.
* **`401 Unauthorized`**: Missing API key in request headers.
* **`403 Forbidden`**: Invalid API key or insufficient scope permissions.
* **`404 Not Found`**: Requested scenario or endpoint does not exist.
* **`413 Payload Too Large`**: Request body exceeds the 64 KB limit.
* **`422 Unprocessable Entity`**: Pydantic schema validation failure.
* **`429 Too Many Requests`**: Token-bucket rate limit exceeded (inspect `Retry-After` header).
* **`500 Internal Server Error`**: Unhandled exception (sanitized in production, full trace logged internally).
* **`503 Service Unavailable`**: Readiness probe failure or server draining.
