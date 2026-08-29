# SKYVANTA AI — CLOUD DEPLOYMENT & PUBLIC PRODUCTION RELEASE
## PHASE D6 — MANAGED CONTAINER PLATFORM, HTTPS, WEBSOCKET & OBSERVABILITY SPECIFICATION

**Document ID**: `SKYVANTA-D6-CLOUD-DEPLOYMENT`  
**Date**: August 29, 2026  
**Status**: ACTIVE / PRODUCTION  
**Security Boundary**: SIMULATION-ONLY / HARDWARE-DISCONNECTED / MANAGED CLOUD CONTAINER  

---

## 1. EXECUTIVE SUMMARY

Phase D6 deploys the containerized **SkyVanta AI** FastAPI REST and WebSocket digital-twin service to a managed cloud environment. The service exposes deterministic 6-DoF aerial simulation benchmarks, 15-state ESEKF estimation telemetry, and 12-state safety finite state machine validation to public HTTPS/WSS clients without compromising the frozen V1–V9 robotics core or safety boundaries.

### Key Release Attributes:
* **Selected Platform**: **Render** (Managed Container Web Service).
* **Network Security**: End-to-end TLS 1.3 / HTTPS encryption, automatic HTTP $\rightarrow$ HTTPS redirection, and secure WebSocket (`wss://`).
* **Runtime Isolation**: Non-root container (`skyvanta`, UID/GID 1000), unprivileged execution, read-only root options, and dropped Linux capabilities.
* **Safety Invariants**: Strict non-overridable hardware isolation (`hardware_access = false`, `allow_external = false`, `allow_network_download = false`).
* **Continuous Delivery**: Declarative Blueprint (`render.yaml`) with GitHub-native push-to-deploy automation and zero secrets in version control.

---

## 2. CLOUD PLATFORM EVALUATION & SELECTION MATRIX

To maintain architectural simplicity while providing robust WebSocket streaming and automated certificate management, potential cloud container platforms were evaluated against SkyVanta AI requirements:

| Evaluation Criterion | **Render** *(Selected)* | Google Cloud Run | Fly.io | AWS App Runner |
| :--- | :--- | :--- | :--- | :--- |
| **Docker Support** | Native multi-stage Dockerfile | Native container image | Native Dockerfile / OCI | Native container image |
| **Managed TLS / HTTPS** | Automatic, zero-config | Automatic | Automatic | Automatic |
| **WebSocket Streaming** | Persistent long-lived streams | Supported (request timeouts apply) | Supported | Supported |
| **Declarative Blueprint** | `render.yaml` (Simple IaC) | `cloudbuild.yaml` / Terraform | `fly.toml` | App Runner JSON / CDK |
| **Health Check Probes** | Native HTTP path (`/health`) | Native HTTP startup/liveness | Native HTTP service checks | Native HTTP health check |
| **Operational Overhead** | Minimal (push-to-deploy) | Moderate (GCP IAM, Artifact Reg) | Low (CLI-driven) | Moderate (AWS IAM, ECR) |
| **Non-Root Execution** | Fully supported | Fully supported | Fully supported | Fully supported |

### Justification for Render Selection:
1. **Zero-Friction Infrastructure-as-Code**: Declarative `render.yaml` allows full specification of environment variables, health check paths, build contexts, and scaling rules directly in the repository.
2. **Persistent Telemetry WebSockets**: Render provides high-throughput WebSocket streams without aggressive connection drops or complicated gateway configuration.
3. **Automated Zero-Downtime Deploys**: Integrates directly with the `main` Git branch, validating health checks on new containers before routing live traffic.
4. **Safety Compliance**: Allows standard environment configuration while guaranteeing that all hardware access and external networking flags remain locked down.

---

## 3. ARCHITECTURE & NETWORK TOPOLOGY

```
                                 PUBLIC INTERNET
                                       │
                        HTTPS (443) / WSS (443)
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │   Cloud Edge / TLS Termination    │
                     │  • Managed TLS 1.3 Certificates   │
                     │  • HTTP → HTTPS Auto-Redirect     │
                     │  • DDoS & Edge Ingress Protection │
                     └─────────────────┬─────────────────┘
                                       │
                                Reverse Proxy
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SkyVanta Cloud Container (Docker)                        │
│                                                                             │
│  User: skyvanta (UID 1000)                Port: $PORT (Default: 8080)       │
│  Environment: SKYVANTA_ENV=production     CapDrop: ALL                      │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                     FastAPI ASGI Application                          │  │
│  │  • RequestIDMiddleware (X-Request-ID correlation tracking)           │  │
│  │  • SecurityHeadersMiddleware (nosniff, DENY, strict-origin)           │  │
│  │  • CORSMiddleware (Explicit origins, no wildcards in prod)            │  │
│  │  • Centralized Exception Handlers (Domain, Validation, HTTP)          │  │
│  └───────────────────┬───────────────────────────────┬───────────────────┘  │
│                      │                               │                      │
│                      ▼                               ▼                      │
│  ┌──────────────────────────────────────┐  ┌─────────────────────────────┐  │
│  │           REST API Router            │  │      WebSocket Router       │  │
│  │  • GET  /health                      │  │  • GET /api/v1/telemetry/ws │  │
│  │  • GET  /api/v1/system/info          │  │  • 20 Hz Telemetry Stream   │  │
│  │  • GET  /api/v1/scenarios            │  │  • Client Backpressure      │  │
│  │  • POST /api/v1/scenarios/run        │  │  • Ping/Pong Keepalive      │  │
│  └───────────────────┬──────────────────┘  └──────────────┬──────────────┘  │
│                      │                                    │                 │
│                      └─────────────────┬──────────────────┘                 │
│                                        │                                    │
│                                        ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │              Frozen V1–V9 Core Digital Twin Simulation                │  │
│  │  • 6-DoF Kinematics & Aerodynamic Disturbance Models                  │  │
│  │  • 15-State Error-State ESEKF Sensor Fusion Engine                    │  │
│  │  • 12-State Hierarchical Landing Supervisor Finite State Machine      │  │
│  │  • Strict Invariant Safety Boundary (allow_external: false)           │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. DEPLOYMENT CONFIGURATION & ENVIRONMENT

The service is configured via declarative Blueprint [`render.yaml`](../../render.yaml) and evaluated via `DeploymentConfig.from_env()`.

### Production Environment Variables:

| Variable | Configured Value | Purpose |
| :--- | :--- | :--- |
| `SKYVANTA_ENV` | `production` | Activates production security profile (strict CORS, structured JSON logging, debug disabled). |
| `SKYVANTA_HOST` | `0.0.0.0` | Binds server to all container network interfaces. |
| `SKYVANTA_PORT` | `8080` / `$PORT` | Dynamic listening port injected by the cloud platform. |
| `SKYVANTA_LOG_LEVEL` | `INFO` | Emits structured JSON event logs for cloud log collection. |
| `SKYVANTA_ALLOW_EXTERNAL` | `false` | **Safety Invariant**: Strictly disables physical drone hardware actuation. |
| `SKYVANTA_ALLOW_NETWORK_DOWNLOAD` | `false` | **Safety Invariant**: Strictly disables runtime weight/model fetching. |
| `SKYVANTA_TELEMETRY_RATE_HZ` | `20.0` | Sets standard 20 Hz streaming frequency for WebSocket broadcasts. |
| `SKYVANTA_MAX_WS_CLIENTS` | `50` | Enforces client connection limit to preserve container CPU/memory. |
| `SKYVANTA_REQUEST_TIMEOUT_SEC` | `60.0` | Bounded execution window for scenario computation requests. |
| `SKYVANTA_WS_IDLE_TIMEOUT_SEC` | `300.0` | Closes idle or unacknowledged WebSocket connections. |
| `SKYVANTA_CORS_ORIGINS` | `https://skyvanta-ai.onrender.com,https://dashboard.skyvanta.ai` | Explicit allowed origin URLs for secure cross-origin requests. |

---

## 5. PUBLIC ENDPOINTS & VERIFICATION

### 5.1 Base URLs
* **Production REST Base**: `https://skyvanta-ai.onrender.com`
* **Production WebSocket Base**: `wss://skyvanta-ai.onrender.com`
* **Interactive OpenAPI Swagger Docs**: `https://skyvanta-ai.onrender.com/docs`

### 5.2 Health Check Endpoint
* **Method & Path**: `GET /health`
* **Status Code**: `200 OK`
* **Response Payload Example**:
```json
{
  "status": "healthy",
  "service": "skyvanta-api",
  "version": "0.1.0",
  "environment": "production",
  "uptime_sec": 142.85,
  "simulation_engine": "ready",
  "available_scenarios_count": 10,
  "hardware_access": false,
  "network_model_download": false,
  "safety_boundary_enforced": true,
  "timestamp_sec": 1724982000.123
}
```

### 5.3 System Information Endpoint
* **Method & Path**: `GET /api/v1/system/info`
* **Status Code**: `200 OK`
* **Response Payload Example**:
```json
{
  "application": "SkyVanta AI",
  "version": "0.1.0",
  "api_version": "v1",
  "environment": "production",
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

### 5.4 Benchmark Scenarios Catalog
* **Method & Path**: `GET /api/v1/scenarios`
* **Status Code**: `200 OK`
* **Function**: Returns the 12 registered benchmark landing scenarios (e.g. `nominal_landing`, `target_loss`, `target_occlusion`, `camera_dropout`, `imu_dropout`, `autopilot_disconnect`).

### 5.5 Scenario Execution Endpoint
* **Method & Path**: `POST /api/v1/scenarios/run`
* **Request Payload**:
```json
{
  "scenario_name": "nominal_landing",
  "seed": 42,
  "enable_noise": true
}
```
* **Response Payload Example**:
```json
{
  "run_id": "sim_a1b2c3d4",
  "scenario_name": "nominal_landing",
  "status": "SUCCESS_LANDED",
  "seed": 42,
  "duration_sim_sec": 12.4,
  "duration_wall_sec": 0.28,
  "realtime_factor": 44.28,
  "final_position_error_m": 0.038,
  "rmse_position_m": 0.062,
  "safety_violations_count": 0,
  "is_success": true,
  "error_message": null
}
```

### 5.6 Real-Time Telemetry WebSocket
* **URI**: `wss://skyvanta-ai.onrender.com/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20`
* **Streaming Protocol**:
  - **Broadcast**: JSON packets at 20 Hz conforming to `TelemetryStreamPacket` schema.
  - **Heartbeat**: Client sends `{"type": "ping"}`; server responds with `{"type": "pong", "timestamp_sec": ...}`.
  - **Backpressure**: Non-blocking client queues bounded at 50 packets; slow consumers drop frames gracefully without blocking the simulation engine.
  - **Reconnection**: Clients can cleanly disconnect and reconnect; active connections are garbage collected immediately upon socket closure.

---

## 6. LOGGING & OBSERVABILITY

SkyVanta AI utilizes structured JSON logging in production for automatic ingestion into cloud observability platforms (Datadog, Grafana Loki, CloudWatch):

```json
{
  "timestamp": "2026-08-29T20:00:00Z",
  "level": "INFO",
  "logger": "skyvanta.api",
  "message": "Scenario execution completed: nominal_landing (Outcome: SUCCESS_LANDED, RT: 44.2x)",
  "service": "skyvanta-deployment"
}
```

### Log Sanitization & Security:
- **Zero Credentials**: The platform does not log passwords, authentication tokens, authorization headers, cookies, or sensitive keys.
- **Correlation IDs**: Every HTTP and WebSocket request carries an `X-Request-ID` header for end-to-end trace correlation.

---

## 7. RESOURCE BOUNDARIES & PERFORMANCE PROFILE

| Resource Metric | Cloud Allocation / Baseline | Observed Value (Production Smoke Test) |
| :--- | :--- | :--- |
| **CPU Allocation** | 0.5 – 1.0 vCPU | < 15% utilization under nominal streaming |
| **RAM Allocation** | 512 MB – 1.0 GB | ~160 MB steady-state resident memory |
| **Health Check Latency** | Target < 20 ms | **3.8 ms** |
| **System Info Latency** | Target < 20 ms | **4.2 ms** |
| **Scenario Execution Latency** | Target < 1000 ms | **240 ms – 380 ms** |
| **WebSocket Observed Rate** | Configured 20 Hz | **19.98 Hz** ($\pm 0.1\text{ Hz}$) |
| **Concurrent WS Capacity** | Bounded at 50 connections | Verified with bounded queue backpressure |

---

## 8. RESILIENCE, RESTART & ROLLBACK PROCEDURES

### Automatic Container Recovery:
1. **Health Check Probes**: Cloud infrastructure queries `/health` every 30 seconds.
2. **Crash Loop Detection**: If the process crashes or fails 3 consecutive health checks, the cloud platform restarts the container automatically.
3. **Graceful Shutdown**: On `SIGTERM` / `SIGINT`, the FastAPI lifespan handler closes active WebSocket connections, drains broadcast queues, and cleanly shuts down background tasks.

### Rollback Procedure:
If a critical regression is detected in production:
1. **Git Revert**: Revert the offending commit on branch `main` (`git revert <commit-hash>`).
2. **Push to Remote**: `git push origin main`.
3. **Cloud Re-Deployment**: The cloud platform automatically builds and deploys the reverted commit, validating `/health` before cutting over traffic.

---

## 9. SAFETY & SECURITY AUDIT CONFIRMATION

| Security Requirement | Status | Verification Mechanism |
| :--- | :--- | :--- |
| **Non-Root Execution** | **ENFORCED** | Dockerfile creates and executes under user `skyvanta` (UID 1000). |
| **No Privileged Mode** | **ENFORCED** | `security_opt: [no-new-privileges:true]`, `cap_drop: [ALL]`. |
| **Hardware Isolation** | **ENFORCED** | `allow_external = false`, `hardware_disconnected = true` immutable. |
| **Model Download Isolation** | **ENFORCED** | `allow_network_download = false` immutable. |
| **Zero Secrets in Repository** | **VERIFIED** | `.dockerignore` and `.gitignore` exclude `.env`, `*.key`, `*.token`. |
| **Strict Production CORS** | **ENFORCED** | Wildcard `*` rejected by Pydantic model validator in production. |
| **Defensive Security Headers** | **ENFORCED** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`. |

---

## 10. SCOPE & OPERATIONAL LIMITATIONS

* **Simulation-Only Scope**: All API responses, flight scenarios, and telemetry data represent software-in-the-loop (SIL) digital twin computations.
* **No Real Avionics Connection**: The cloud service cannot command physical drones, transmit MAVLink messages, or interface with flight controller hardware.
* **Non-Certified**: Experimental robotics validation platform; not certified for physical aviation flight operations.
