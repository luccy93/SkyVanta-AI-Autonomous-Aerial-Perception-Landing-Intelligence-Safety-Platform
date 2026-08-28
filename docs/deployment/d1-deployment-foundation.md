# SKYVANTA AI — DEPLOYMENT ARCHITECTURE & FOUNDATION
## PHASE D1 — DEPLOYMENT SPECIFICATION & SERVICE BOUNDARY

**Document ID**: `SKYVANTA-D1-DEPLOYMENT-FOUNDATION`  
**Date**: August 28, 2026  
**Status**: ACTIVE  
**Security Boundary**: SIMULATION-ONLY / HARDWARE-DISCONNECTED  

---

## 1. EXECUTIVE OVERVIEW

The SkyVanta AI deployment layer encapsulates the core V1–V9 perception, state estimation, safety intelligence, and digital twin simulation engines into a clean, containerized, API-accessible software service layer.

The deployment architecture is strictly decoupled from core algorithms:
- Core estimation, vision, tracking, and safety pipelines (`skyvanta/core/`, `perception/`, `fusion/`, `intelligence/`, etc.) remain **100% frozen and unmodified**.
- The deployment layer (`skyvanta/deployment/`) provides configuration models, health contracts, structured logging, and boundary abstractions.
- Physical flight hardware, MAVLink telemetry, serial ports, and remote model downloads remain **permanently disconnected and disabled by default**.

---

## 2. DEPLOYMENT ARCHITECTURE

```
                               +----------------------------------------+
                               |     Future Next.js Web Dashboard       |
                               |    (React / WebGL / Chart Telemetry)   |
                               +-------------------+--------------------+
                                                   |
                             REST API (Port 8080)  |  WebSocket Stream (20 Hz)
                                                   v
+----------------------------------------------------------------------------------------+
|                          SkyVanta AI Deployment Layer                                  |
|                            (skyvanta.deployment)                                       |
|                                                                                        |
|   +-----------------------+   +-----------------------+   +------------------------+   |
|   |   DeploymentConfig    |   |  HealthCheckService   |   |    DeploymentLogger    |   |
|   | (Env Tiers & Invar.)  |   |  (/health & Status)   |   |   (Structured JSON)    |   |
|   +-----------+-----------+   +-----------+-----------+   +-----------+------------+   |
|               |                           |                           |                |
+---------------|---------------------------|---------------------------|----------------+
                |                           |                           |
                +---------------------------+---------------------------+
                                            |
                                            v
+----------------------------------------------------------------------------------------+
|                            SkyVanta AI V1–V9 Core Engine                               |
|                                                                                        |
|   [Perception V2] ---> [Tracking V3] ---> [PnP V4] ---> [SE3 Spatial Graph V5]         |
|                                                                 |                      |
|   [Digital Twin V9] <--- [Flight Auth V8] <--- [Safety FSM V7] <--- [15-State ESEKF]   |
+----------------------------------------------------------------------------------------+
```

---

## 3. ENVIRONMENT CONFIGURATION STRATEGY

The deployment layer introduces `DeploymentConfig`, which supports three operational tiers with strict safety defaults:

| Tier | Enum Value | Purpose | Default Host / Port | Default Log Level |
|---|---|---|---|---|
| **Development** | `development` | Local interactive debugging and testing | `0.0.0.0:8080` | `INFO` (Human-formatted) |
| **Testing** | `testing` | CI/CD automated integration & health checks | `127.0.0.1:8080` | `DEBUG` |
| **Production** | `production` | Containerized cloud / server deployment | `0.0.0.0:8080` | `INFO` (Structured JSON) |

### Environment Variables
All configuration options can be passed through standard environment variables:
- `SKYVANTA_ENV`: `development` | `testing` | `production` (default: `development`)
- `SKYVANTA_HOST`: Bind address (default: `0.0.0.0`)
- `SKYVANTA_PORT`: Bind port (default: `8080`)
- `SKYVANTA_LOG_LEVEL`: `DEBUG` | `INFO` | `WARNING` | `ERROR` (default: `INFO`)
- `SKYVANTA_CORS_ORIGINS`: Comma-separated list of allowed frontend origins (e.g. `http://localhost:3000`)
- `SKYVANTA_TELEMETRY_RATE_HZ`: Telemetry broadcast frequency cap (default: `20.0`)
- `SKYVANTA_ENABLE_METRICS`: `true` | `false` (default: `true`)

---

## 4. SECURITY & HARDWARE ISOLATION BOUNDARIES

The deployment layer enforces hardcoded, non-overridable security invariants:

1. **Hardware Disconnected (`hardware_disconnected = True`)**:
   - Zero physical serial port listeners.
   - Zero live UDP/TCP MAVLink bridges.
   - Zero hardware PWM or ESC control channels.
2. **External Actuation Blocked (`allow_external = False`)**:
   - Outbound flight commands are strictly routed to the Software-in-the-Loop `MockAutopilot` and simulation digital twin.
3. **No Automatic Network Downloads (`allow_network_download = False`)**:
   - Model weights and assets must be pre-packaged locally; runtime HTTP/HTTPS fetching of model files is disabled.
4. **Secret Isolation**:
   - Zero API tokens, passwords, or credentials are required or embedded in deployment configurations.

---

## 5. HEALTH CHECK CONTRACTS

The `/health` endpoint is serviced by `HealthCheckService` and returns the `DeploymentHealthContract` schema:

```json
{
  "status": "healthy",
  "service": "skyvanta-api",
  "version": "0.1.0",
  "environment": "production",
  "uptime_sec": 142.53,
  "simulation_engine": "ready",
  "available_scenarios_count": 12,
  "hardware_access": false,
  "network_model_download": false,
  "safety_boundary_enforced": true,
  "timestamp_sec": 1724844600.12
}
```

### Health Status Logic:
- **`healthy`**: Scenario catalog fully registered ($\ge 10$ scenarios) and all safety isolation boundaries intact.
- **`degraded`**: Scenarios registered but partial configuration warnings detected.
- **`unhealthy`**: Scenario registry failed or safety boundary breach detected.

---

## 6. DOCKER EXECUTION STRATEGY

A minimal, secure Docker container is defined via `Dockerfile`:

- **Base Image**: `python:3.11-slim`
- **Security**: Runs under an unprivileged system user (`skyvanta:skyvanta`, UID 1000).
- **Isolation**: Only necessary package sources and runtime dependencies installed.
- **Healthcheck**: Periodically executes container healthcheck evaluating `HealthCheckService.check_health()`.
- **Port Exposure**: Port `8080` exposed for REST API and WebSocket streaming.

### Docker Commands
```bash
# Build the production image
docker build -t skyvanta-ai:latest .

# Run the container
docker run -p 8080:8080 --rm skyvanta-ai:latest
```

---

## 7. FUTURE NEXT.JS DASHBOARD INTEGRATION

The deployment boundary is designed to interface seamlessly with a future Next.js web application:
1. **REST Endpoints**:
   - `GET /health`: Service health and safety boundary verification.
   - `GET /api/scenarios`: List all available benchmark scenarios (`nominal_landing`, `target_loss`, etc.).
   - `POST /api/scenarios/run`: Execute a scenario and return quantitative validation results.
2. **WebSocket Streaming**:
   - `WS /ws/telemetry`: 20 Hz streaming of vehicle position, orientation (RPY), landing phase, estimated covariance trace, and real-time safety status.
