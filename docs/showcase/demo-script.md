# SkyVanta AI — Live Technical Demonstration Script (3–5 Minutes)

## Overview & Demo Goal
This script guides a live or recorded technical demonstration showcasing the **SkyVanta AI** robotics and deployment architecture.

---

## Timecoded Walkthrough

### `00:00 — 00:30` | Project Introduction & Context
* **Presenter:** "Welcome to SkyVanta AI. This platform solves the problem of GPS-denied autonomous aerial landing by fusing high-rate inertial measurements with monocular computer vision through a 15-state Error-State Extended Kalman Filter and deterministic safety supervision."
* **Screen:** Open GitHub Repository `README.md` showcasing the system overview and badges.

---

### `00:30 — 01:00` | High-Level Architecture
* **Presenter:** "The platform is structured into two decoupled domains: the frozen algorithmic robotics core (Volumes V1–V9: perception, tracking, 6-DoF PnP, spatial localization, 15-state ESEKF on $SO(3)$, safety supervision, and 6-DoF digital twin simulation) and the production deployment envelope (Phases D1–D10: hardened container, FastAPI backend, 20 Hz WebSocket streaming, API key authentication, and disaster recovery)."
* **Screen:** Display `docs/architecture/skyvanta-system-architecture.md` diagram.

---

### `01:00 — 01:30` | Service Launch & Pre-Flight Verification
* **Presenter:** "We run our pre-flight release verification via the CLI: `python -m skyvanta release`. This inspects configuration invariants, ensures physical hardware access is disabled, and audits metadata against secret leaks."
* **Terminal Action:**
  ```bash
  python -m skyvanta release
  ```
* **Output Highlight:** Show `RELEASE STATUS: READY` and `Hardware Access: DISABLED`.

---

### `01:30 — 02:00` | Health & System Information Endpoints
* **Presenter:** "Our service is live with public probe endpoints and authenticated metadata APIs."
* **Actions:**
  - Show `GET /health` in browser or curl:
    ```json
    {
      "status": "healthy",
      "simulation_engine": "ready",
      "hardware_access": false,
      "safety_boundary_enforced": true
    }
    ```
  - Show Swagger UI at `http://localhost:8080/docs`.

---

### `02:00 — 02:30` | Benchmark Scenario Execution (`nominal_landing`)
* **Presenter:** "Now let's execute the `nominal_landing` benchmark scenario via the REST API. The digital twin runs the 6-DoF physics simulation, rendering frames through perception, PnP pose estimation, ESEKF sensor fusion, and the safety state machine."
* **Action:**
  ```bash
  curl -X POST http://localhost:8080/api/v1/scenarios/run \
    -H "Authorization: Bearer sk_test_admin_key_12345" \
    -H "Content-Type: application/json" \
    -d '{"scenario_name": "nominal_landing", "seed": 42}'
  ```
* **Highlight:** Show result: `SUCCESS_LANDED`, Final Error: `0.0000 m`, RMSE: `0.0143 m`, Realtime Factor: `56.32x`.

---

### `02:30 — 03:00` | Real-Time WebSocket Telemetry
* **Presenter:** "In addition to batch execution, operators connect to our 20 Hz WebSocket stream to receive continuous 6-DoF vehicle position, orientation, velocity, and supervisory landing phase state."
* **Action:** Connect WebSocket client to `/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20`.
* **Highlight:** Stream incoming JSON packets showing monotonic timestamps and state transitions: `SEARCHING` $\rightarrow$ `ALIGNING` $\rightarrow$ `APPROACHING` $\rightarrow$ `DESCENDING` $\rightarrow$ `FINAL_APPROACH`.

---

### `03:00 — 03:30` | Safety Supervision & Abort Invariant
* **Presenter:** "If target tracking is lost or covariance exceeds $0.25\text{ m}$, our safety supervisor immediately triggers `ABORTING`. Our state transition matrix guarantees that an abort can never transition to descent."
* **Screen:** Show `docs/architecture/v7-state-machine.md` and transition matrix code in `skyvanta/intelligence/states.py`.

---

### `03:30 — 04:00` | Production Observability & Metrics
* **Presenter:** "For zero-SSH operations, the platform provides application-level metrics via `GET /api/v1/metrics`."
* **Action:** Query `/api/v1/metrics`. Show latency percentiles (p50/p95/p99), error counters, active WebSocket client counts, and memory RSS footprint.

---

### `04:00 — 04:30` | Container Hardening & Cloud Infrastructure
* **Presenter:** "The deployment is containerized with non-root user execution, `cap_drop: [ALL]`, `no-new-privileges:true`, and deployed declaratively via `render.yaml` with automated TLS 1.3 encryption."
* **Screen:** Show `Dockerfile` and `compose.yaml`.

---

### `04:30 — 05:00` | Test Suite & Conclusion
* **Presenter:** "The entire codebase is verified by 437 automated tests with 100% pass rate, zero unsafe primitives, and zero hardware connections. SkyVanta AI delivers production-grade robotics intelligence ready for enterprise deployment."
* **Action:**
  ```bash
  pytest -q
  ```
* **Output:** `437 passed, 0 failed in ~24s`.
