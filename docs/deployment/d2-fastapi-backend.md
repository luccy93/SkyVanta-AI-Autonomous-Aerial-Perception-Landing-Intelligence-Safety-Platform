# SKYVANTA AI — FASTAPI BACKEND & REST SERVICE LAYER
## PHASE D2 — API SERVICE ARCHITECTURE & CONTRACT SPECIFICATION

**Document ID**: `SKYVANTA-D2-FASTAPI-BACKEND`  
**Date**: August 28, 2026  
**Status**: ACTIVE  
**Security Boundary**: SIMULATION-ONLY / HARDWARE-DISCONNECTED  

---

## 1. EXECUTIVE OVERVIEW

Phase D2 implements a production-grade, asynchronous **FastAPI service layer** (`skyvanta/deployment/api/`) wrapping the frozen V1–V9 robotics core. 

The API layer acts as a pure software gateway:
- Exposes digital twin scenario management and execution to external clients.
- Provides standard health monitoring and capability discovery.
- Injects correlation request identifiers (`X-Request-ID`) across all operations.
- Enforces strict simulation-only boundaries (`hardware_access: false`, `network_model_download: false`).

---

## 2. API ARCHITECTURE & DATA FLOW

```
                          Client / Dashboard
                                  |
                   HTTP Request (with X-Request-ID)
                                  v
+-------------------------------------------------------------------+
|                     FastAPI Application Layer                     |
|                                                                   |
|   +---------------------+   +---------------------------------+   |
|   |  CORS Middleware    |   |    RequestIDMiddleware          |   |
|   | (Configured Origins)|   |    (UUID4 Correlation Tracing)  |   |
|   +----------+----------+   +----------------+----------------+   |
|              |                               |                    |
|              v                               v                    |
|   +-----------------------------------------------------------+   |
|   |                      Route Handlers                       |   |
|   |   GET  /health                                            |   |
|   |   GET  /api/v1/system/info                                |   |
|   |   GET  /api/v1/scenarios                                  |   |
|   |   GET  /api/v1/scenarios/{name}                           |   |
|   |   POST /api/v1/scenarios/run                              |   |
|   +------------------------------+----------------------------+   |
+----------------------------------|--------------------------------+
                                   |
                         Async Threadpool Offload
                                   |
                                   v
+-------------------------------------------------------------------+
|               SimulationService Adapter Boundary                  |
|                  (skyvanta.deployment.api)                        |
|                                                                   |
|   +--------------------+     +--------------------------------+   |
|   |  ScenarioRegistry  |     |         ScenarioEngine         |   |
|   |  (12 Catalog Items)|     |   (Closed-Loop 6-DoF Twin)     |   |
|   +--------------------+     +--------------------------------+   |
+-------------------------------------------------------------------+
```

---

## 3. REST ENDPOINT SPECIFICATION

| Method | Endpoint Path | Tag | Description | Request Body | Response Model |
|---|---|---|---|---|---|
| **`GET`** | `/health` | `Health` | Infrastructure health, catalog count, and safety isolation status | None | `DeploymentHealthContract` |
| **`GET`** | `/api/v1/system/info` | `System` | Platform versioning, metadata, and supported capabilities | None | `SystemInfoResponse` |
| **`GET`** | `/api/v1/scenarios` | `Scenarios` | Catalog list of all 12 standard benchmark landing scenarios | None | `List[ScenarioCatalogItem]` |
| **`GET`** | `/api/v1/scenarios/{scenario_name}` | `Scenarios` | Full kinematic and event definition of a specific scenario | None | `ScenarioDetailItem` |
| **`POST`** | `/api/v1/scenarios/run` | `Simulation` | Executes 6-DoF digital twin scenario and returns compliance metrics | `ScenarioRunRequest` | `ScenarioRunResponse` |

---

## 4. REQUEST & RESPONSE CONTRACTS

### 1. `GET /health` Response Example
```json
{
  "status": "healthy",
  "service": "skyvanta-api",
  "version": "0.1.0",
  "environment": "production",
  "uptime_sec": 142.85,
  "simulation_engine": "ready",
  "available_scenarios_count": 12,
  "hardware_access": false,
  "network_model_download": false,
  "safety_boundary_enforced": true,
  "timestamp_sec": 1724845000.12
}
```

### 2. `POST /api/v1/scenarios/run`
**Request Payload (`ScenarioRunRequest`)**:
```json
{
  "scenario_name": "nominal_landing",
  "seed": 42,
  "max_duration_sec": 20.0,
  "enable_noise": true
}
```

**Response Payload (`ScenarioRunResponse`)**:
```json
{
  "run_id": "api_run_nominal_landing_42_a1b2c3d4",
  "scenario_name": "SCN_NOMINAL_01",
  "status": "SUCCESS_LANDED",
  "seed": 42,
  "duration_sim_sec": 15.85,
  "duration_wall_sec": 0.482,
  "realtime_factor": 32.88,
  "final_position_error_m": 0.0,
  "rmse_position_m": 0.0143,
  "safety_violations_count": 0,
  "is_success": true,
  "error_message": null
}
```

---

## 5. CENTRALIZED ERROR HANDLING

All errors return structured JSON payloads with correlated `request_id`:

| Error Type | HTTP Status | Error Code | Response Schema |
|---|---|---|---|
| Unknown Scenario | `404 Not Found` | `scenario_not_found` | `{"error": "scenario_not_found", "message": "...", "request_id": "..."}` |
| Validation Error | `422 Unprocessable`| `validation_error` | `{"error": "validation_error", "message": "...", "details": [...], "request_id": "..."}` |
| Domain Error | `400 Bad Request` | `skyvanta_domain_error` | `{"error": "skyvanta_domain_error", "message": "...", "request_id": "..."}` |
| Internal Exception | `500 Server Error`| `internal_server_error` | `{"error": "internal_server_error", "message": "...", "request_id": "..."}` |

---

## 6. LOCAL & DOCKER STARTUP

### 1. Run Locally with Uvicorn
```bash
# Start API server in development mode
uvicorn skyvanta.deployment.api.app:app --host 0.0.0.0 --port 8080 --reload
```

### 2. Run with Docker
```bash
# Build production Docker image
docker build -t skyvanta-ai:latest .

# Run container exposing port 8080
docker run -p 8080:8080 --rm skyvanta-ai:latest
```

### 3. Interactive OpenAPI Documentation
Open in your browser:
- **Swagger UI**: [http://localhost:8080/docs](http://localhost:8080/docs)
- **ReDoc**: [http://localhost:8080/redoc](http://localhost:8080/redoc)
- **Raw OpenAPI JSON**: [http://localhost:8080/openapi.json](http://localhost:8080/openapi.json)

---

## 7. SECURITY & HARDWARE ISOLATION GUARANTEES

- **Zero Physical Hardware**: The API server operates in user space and does not access `/dev/tty*`, COM ports, or physical buses.
- **Zero Remote Downloads**: All algorithms operate strictly offline without external weight downloads.
- **No Background Zombie Threads**: Simulation jobs run synchronously within the threadpool executor without detached daemon leaks.
