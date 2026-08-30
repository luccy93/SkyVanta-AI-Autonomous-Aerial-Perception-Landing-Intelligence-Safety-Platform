# SKYVANTA AI — PRODUCTION OBSERVABILITY, MONITORING & OPERATIONS
## PHASE D7 — APPLICATION-LEVEL TELEMETRY, HEALTH/READINESS PROBES, STRUCTURED EVENTS & OPERATOR RUNBOOK

**Document ID**: `SKYVANTA-D7-OBSERVABILITY-OPERATIONS`  
**Date**: August 30, 2026  
**Status**: ACTIVE / PRODUCTION  
**Security Boundary**: SIMULATION-ONLY / BOUNDED CARDINALITY / ZERO SECRETS IN TELEMETRY  

---

## 1. EXECUTIVE SUMMARY

Phase D7 introduces a dedicated, production-grade observability and runtime monitoring subsystem for the deployed SkyVanta AI service. Designed for zero-SSH cloud deployments (e.g., Render, Kubernetes, Docker), this layer exposes machine-readable operational metrics, exact latency percentiles, structured JSON audit events, decoupled liveness/readiness probes, and configurable resource warnings without altering the frozen V1–V9 robotics core, perception algorithms, or safety supervisor logic.

```
+-----------------------------------------------------------------------------------+
|                            PUBLIC / OPERATOR TRAFFIC                              |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                        FASTAPI APPLICATION BOUNDARY LAYER                         |
|                                                                                   |
|  [SecurityHeadersMiddleware] -> [ObservabilityMiddleware] -> [RateLimiter]       |
|                                         |                                         |
|                 +-----------------------+-----------------------+                 |
|                 |                       |                       |                 |
|                 v                       v                       v                 |
|       +-------------------+   +-------------------+   +-------------------+       |
|       | MetricsCollector  |   |    EventLogger    |   |  ResourceMonitor  |       |
|       | • Request Volumes |   | • JSON Events     |   | • CPU / RSS Memory|       |
|       | • p50/p95/p99 Lat |   | • Secret Scrub    |   | • Uptime & Commit |       |
|       | • WS / Scenarios  |   | • Bounded Ring    |   | • Warning Checks  |       |
|       +-------------------+   +-------------------+   +-------------------+       |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         OPERATIONAL REST & WS ENDPOINTS                           |
|                                                                                   |
|  GET /health            -> Infrastructure Liveness Contract                       |
|  GET /ready             -> Operational Dependency Readiness Contract              |
|  GET /api/v1/metrics    -> Machine-Readable Observability Metrics                 |
|  GET /api/v1/system/info-> System Version, Git SHA & Capabilities                 |
|  WS  /api/v1/telemetry/ws -> Streaming Telemetry with Transmit Counters           |
+-----------------------------------------------------------------------------------+
```

---

## 2. OBSERVABILITY ARCHITECTURE

The observability subsystem is housed cleanly under `skyvanta/deployment/observability/` with strict separation of responsibilities:

| Module | Responsibility | Cardinality & Retention Strategy |
| :--- | :--- | :--- |
| `events.py` | Structured event schema, secret redaction, and bounded event publishing. | In-memory circular buffer ($N=100$), JSON stdout output for cloud ingestion. |
| `metrics.py` | Request counters, error classification, WebSocket metrics, and exact latency percentiles. | Bounded route templates (no arbitrary path labels), rolling $N=1000$ latency deques. |
| `health.py` | Dedicated `ReadinessService` verifying genuine operational dependencies. | Lightweight on-demand evaluations; no external synthetic dependencies. |
| `runtime.py` | Process CPU%, RSS memory, uptime, Git commit resolution, and threshold warnings. | Real-time process inspection via `psutil` with pure stdlib fallbacks. |
| `middleware.py` | Timing middleware, slow request detection ($>1000\text{ ms}$), and token-bucket rate limiting. | High-resolution `time.perf_counter()`, per-client bounded IP tracking. |

---

## 3. PROBES & API CONTRACTS

### 3.1. Liveness Probe (`GET /health`)
* **Purpose**: Verifies that the FastAPI process is alive, responding, and enforcing safety boundaries.
* **HTTP Status**: `200 OK` (Healthy/Degraded), `503 Service Unavailable` (Unhealthy).
* **Contract Schema (`DeploymentHealthContract`)**:
```json
{
  "status": "healthy",
  "service": "skyvanta-api",
  "version": "0.1.0",
  "environment": "production",
  "uptime_sec": 1420.55,
  "simulation_engine": "ready",
  "available_scenarios_count": 10,
  "hardware_access": false,
  "network_model_download": false,
  "safety_boundary_enforced": true,
  "timestamp_sec": 1756540800.123
}
```

### 3.2. Readiness Probe (`GET /ready`)
* **Purpose**: Verifies that genuine operational dependencies are loaded and ready to serve traffic before the cloud ingress routes live users.
* **Checks Performed**:
  1. `scenario_catalog_loaded`: Verified standard benchmark scenario catalog registered ($\ge 10$ scenarios).
  2. `simulation_engine_ready`: Verified `ScenarioEngine` can be instantiated without runtime dependency errors.
  3. `safety_invariants_enforced`: Verified `hardware_disconnected == True`, `allow_external == False`, and `allow_network_download == False`.
* **HTTP Status**: `200 OK` (when ready), `503 Service Unavailable` (when not ready).
* **Contract Schema (`DeploymentReadinessContract`)**:
```json
{
  "ready": true,
  "status": "ready",
  "service": "skyvanta-api",
  "version": "0.1.0",
  "environment": "production",
  "checks": {
    "scenario_catalog_loaded": true,
    "simulation_engine_ready": true,
    "safety_invariants_enforced": true
  },
  "uptime_sec": 1420.55,
  "timestamp_sec": 1756540800.125
}
```

### 3.3. Machine-Readable Metrics Endpoint (`GET /api/v1/metrics`)
* **Purpose**: Single unified endpoint for SREs, monitoring dashboards, and scraping tools.
* **Contract Schema (`MetricsResponseContract`)**:
```json
{
  "service": "skyvanta-api",
  "version": "0.1.0",
  "environment": "production",
  "timestamp_sec": 1756540800.130,
  "http": {
    "total_requests": 14250,
    "successful_requests": 14230,
    "failed_requests": 20,
    "slow_requests": 2,
    "requests_by_method": {"GET": 12000, "POST": 2250},
    "requests_by_endpoint": {
      "/health": 5000,
      "/ready": 5000,
      "/api/v1/system/info": 1000,
      "/api/v1/metrics": 1000,
      "/api/v1/scenarios": 200,
      "/api/v1/scenarios/run": 1000,
      "/api/v1/telemetry/ws": 50
    },
    "requests_by_status": {"200": 14230, "404": 15, "422": 5},
    "latency_overall": {
      "min_ms": 0.45,
      "avg_ms": 1.82,
      "median_ms": 1.20,
      "p95_ms": 4.50,
      "p99_ms": 12.80,
      "max_ms": 45.20,
      "sample_count": 1000
    }
  },
  "errors": {
    "validation_errors": 5,
    "scenario_execution_failures": 0,
    "internal_errors": 0,
    "websocket_errors": 2,
    "config_failures": 0,
    "startup_failures": 0,
    "total_errors": 7
  },
  "websockets": {
    "active_connections": 3,
    "total_connections": 48,
    "disconnects": 45,
    "telemetry_packets_sent": 84200,
    "dropped_packets": 0,
    "heartbeat_failures": 1,
    "configured_stream_rate_hz": 20.0,
    "observed_stream_rate_hz": 19.98,
    "duration_stats": {"avg_sec": 42.5, "min_sec": 1.2, "max_sec": 180.0}
  },
  "scenarios": {
    "total_executions": 340,
    "successful_executions": 335,
    "failed_executions": 5,
    "scenarios": {
      "nominal_landing": {
        "executions": 200,
        "successful_executions": 200,
        "failed_executions": 0,
        "avg_duration_wall_sec": 0.22,
        "avg_realtime_factor": 82.5,
        "avg_final_position_error_m": 0.0345,
        "decisions_breakdown": {"SUCCESS_LANDED": 200}
      }
    }
  },
  "system": {
    "uptime_sec": 1420.55,
    "cpu_percent": 12.4,
    "memory_rss_mb": 118.5,
    "python_version": "3.11.9",
    "git_commit": "5c95893415c26076adf3e86abc3af3cf1635adc9",
    "build_timestamp": "2026-08-30T00:00:00Z"
  },
  "warnings": [],
  "recent_events": [
    {
      "event_type": "SERVICE_READY",
      "timestamp": "2026-08-30T12:00:05Z",
      "severity": "INFO",
      "message": "SkyVanta AI service is verified ready to serve traffic",
      "details": {"available_scenarios": 10}
    }
  ]
}
```

---

## 4. STRUCTURED EVENT AUDITING & SECURITY REDACTION

### 4.1. Canonical Event Types
All major operational lifecycle events are emitted as structured single-line JSON logs to `stdout`:
* `SERVICE_STARTED`: Process startup with bound host/port.
* `SERVICE_READY`: Readiness verification passed.
* `SERVICE_SHUTDOWN`: Graceful termination.
* `REQUEST_ERROR`: Unhandled exception or domain error.
* `SCENARIO_STARTED`: Benchmark execution initiated.
* `SCENARIO_COMPLETED`: Benchmark execution completed.
* `SCENARIO_FAILED`: Simulation execution threw an exception.
* `WEBSOCKET_CONNECTED`: Client established a WebSocket connection.
* `WEBSOCKET_DISCONNECTED`: Client closed connection (includes duration).
* `HEARTBEAT_FAILURE`: Malformed message or ping timeout.
* `RESOURCE_WARNING`: CPU, memory, or connection limit approaching threshold.
* `SLOW_REQUEST`: Request duration exceeded `slow_request_threshold_ms`.
* `RATE_LIMIT_EXCEEDED`: Client request exceeded token-bucket capacity.

### 4.2. Secret Redaction Policy
To guarantee zero secret leakage in logs or telemetry, `redact_sensitive_data()` recursively scrubs:
* `Authorization` headers (including `Bearer` tokens).
* `Cookie` and `Set-Cookie` values.
* Keys matching `password`, `passwd`, `secret`, `token`, `auth`, `api_key`, `credential`, `private_key`.
* Replaces values with `[REDACTED]`.

---

## 5. RESOURCE WARNING THRESHOLDS & RATE LIMITING

### 5.1. Non-Intrusive Resource Warnings
Configurable thresholds in `DeploymentConfig`:
* `cpu_warning_threshold_pct`: Default `85.0%`.
* `memory_warning_threshold_mb`: Default `512.0 MB`.
* `ws_client_warning_pct`: Default `80.0%` of `max_ws_clients`.

> [!NOTE]
> Resource warnings are strictly operational diagnostics. They never alter flight guidance commands, V7 safety decisions, or digital twin physics.

### 5.2. REST API Rate Limiting
* **Mechanism**: Token Bucket per client IP address.
* **Default Rate**: `120 requests/minute` with a burst capacity of `30`.
* **Exempt Routes**: `/health`, `/ready`, `/api/v1/telemetry/ws` (WebSocket connection rate is managed independently via `max_ws_clients`).
* **Response**: `429 Too Many Requests` with `Retry-After: 5` header.

---

## 6. SRE OPERATIONAL RUNBOOK

| Symptom | Diagnostic Step | Mitigation |
| :--- | :--- | :--- |
| `GET /ready` returns `503` | Check `checks` dictionary in response payload. | Verify scenario catalog or configuration integrity. |
| High p99 Latency ($>100\text{ ms}$) | Inspect `/api/v1/metrics` `latency_by_endpoint`. | Identify slow route; check system CPU in `system.cpu_percent`. |
| WebSocket Drops | Check `websockets.dropped_packets` and `websockets.active_connections`. | Client network connection buffer saturation or client processing delay. |
| Memory Growth Warning | Inspect `system.memory_rss_mb` over time. | In-memory deques are strictly bounded ($O(1)$). Heavy garbage collection or large simulation batches. |
| Excessive 429 Errors | Check `recent_events` for `RATE_LIMIT_EXCEEDED`. | Client script flooding API; configure batching or increase `SKYVANTA_RATE_LIMIT_RPM`. |

---

## 7. CLOUD PLATFORM COMPATIBILITY

* **Render**: Integrates natively with `render.yaml` health checks on `/health` and zero-downtime traffic cutover on `/ready`. Logs are streamed to Render Log Streams.
* **Docker / Containers**: Runs as unprivileged user `skyvanta` (UID 1000), compatible with read-only root filesystems, dropped capabilities (`cap_drop: [ALL]`), and zero external network access.
* **Zero Infrastructure Overhead**: Operates entirely within the Python runtime without requiring separate Prometheus daemon processes, node exporters, or root access.
