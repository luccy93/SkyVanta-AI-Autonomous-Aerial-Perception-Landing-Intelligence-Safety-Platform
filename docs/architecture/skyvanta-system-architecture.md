# SkyVanta AI — Complete System Architecture Specification

## 1. High-Level Architecture Overview

**SkyVanta AI** is an enterprise-grade, software-in-the-loop (SITL) autonomous aerial landing perception, 15-state sensor fusion, safety supervision, and digital twin simulation platform.

The system is partitioned into two distinct, decoupled layers:
1. **Robotics & Simulation Core (Volumes V1–V9)**: Complete and frozen algorithmic pipeline.
2. **Production Deployment & Reliability Envelope (Phases D1–D9)**: Hardened container, API, WebSocket, security, observability, release engineering, and disaster recovery layer.

```mermaid
graph TD
    subgraph "DEPLOYMENT LAYER (D1-D9)"
        Edge["Cloud Edge / Ingress (Render / Docker)"]
        Sec["Security Middleware (Auth / Scopes / Rate Limit / Headers)"]
        Obs["Observability (Metrics / JSON Logs / Event Stream)"]
        Rel["Reliability & Release (StartupValidator / ShutdownCoordinator / Recovery)"]
        API["FastAPI App (REST /health, /ready, /api/v1/*)"]
        WS["WebSocket Telemetry Broadcast (/api/v1/telemetry/ws)"]
    end

    subgraph "ROBOTICS CORE (V1-V9 FROZEN)"
        DT["V9 Digital Twin 6-DoF Dynamics & Environment Engine"]
        Percept["V2 Perception Engine (Fiducial / Motion Contrast / YOLO)"]
        Track["V3 Multi-Target Kalman Tracking & Association"]
        PnP["V4 Monocular 6-DoF PnP Pose Solver (SQPnP / IPPE)"]
        Spatial["V5 SE(3) Spatial Localization & Frame Graph"]
        ESEKF["V6 15-State Error-State Extended Kalman Filter (Lie Group SO(3))"]
        Intel["V7 Landing Intelligence & 12-State Safety Supervisor FSM"]
        Flight["V8 Flight Interface & Command Rate Authorization"]
    end

    Edge --> Sec
    Sec --> Rel
    Rel --> API
    API --> Obs
    API --> WS

    API --> DT
    WS --> DT

    DT -->|Synthetic RGB Frame| Percept
    DT -->|IMU / Altimeter / Gyro| ESEKF

    Percept -->|Target Detections| Track
    Track -->|Confirmed Track Box| PnP
    PnP -->|Relative Pose T_c_t| Spatial
    Spatial -->|Fused SE(3) Pose| ESEKF

    ESEKF -->|15-State Navigation State| Intel
    Intel -->|Supervisory Decision & Phase| Flight
    Flight -->|Authorized Flight Command| DT
    Flight -->|Validated Telemetry Packet| WS
```

---

## 2. Robotics Core Subsystems (Volumes V1–V9)

```
                 SKYVANTA AI
                      │
 ┌────────────────────┴────────────────────┐
 │                                         │
ROBOTICS CORE                         DEPLOYMENT
V1–V9                                 D1–D9
 │                                         │
 ├─ V1 Architecture Foundation             ├─ D1 Deployment Foundation
 ├─ V2 Perception Engine                   ├─ D2 FastAPI Backend
 ├─ V3 Multi-Target Tracking               ├─ D3 WebSocket Telemetry
 ├─ V4 6-DoF PnP Pose Estimation           ├─ D4 Hardened Docker
 ├─ V5 SE(3) Spatial Localization          ├─ D5 Production Config
 ├─ V6 15-State ESEKF Sensor Fusion        ├─ D6 Cloud Deployment
 ├─ V7 Safety Supervisor FSM               ├─ D7 Observability & Ops
 ├─ V8 Flight Command Interface            ├─ D8 Security & Auth
 └─ V9 Digital Twin Scenario Engine        └─ D9 Release & Recovery
 │
 └───────────────┬─────────────────────────┘
                 │
          SOFTWARE-IN-LOOP
          SIMULATION ONLY
```

### Volume V1: Architecture Foundation
- Structured Pydantic contracts, deterministic configuration schemas, and coordinate frame definitions.
- Modular decoupled design enabling zero-regression pipeline upgrades.

### Volume V2: Computer-Vision Perception
- Multi-tier detection: High-precision fiducial geometric detection, motion contrast subtraction, and optional local YOLO inference.
- Noise filtering, corner validation, and sub-pixel edge refinement.

### Volume V3: Multi-Target Tracking
- 8-state constant velocity Kalman filter tracking vehicle and pad kinematics.
- Multi-cue data association with Mahalanobis distance gating and track life-cycle management (Tentative, Confirmed, Lost, Deleted).

### Volume V4: PnP / 6-DoF Pose Estimation
- Robust monocular Perspective-n-Point pose solver utilizing SQPnP and IPPE with planar landing pad geometry.
- Reprojection error minimization and geometric sanity checks.

### Volume V5: SE(3) Spatial Localization
- Kinematic frame graph managing coordinate transformations ($\text{World } \rightarrow \text{Body } \rightarrow \text{Camera } \rightarrow \text{Target}$).
- Lie-group transformations and numerical singularity mitigation.

### Volume V6: 15-State Error-State EKF (ESEKF)
- Continuous-discrete 15-state navigation filter on manifold:
  - Nominal states: Position ($3$), Velocity ($3$), Attitude Quaternions ($4$), Accel Bias ($3$), Gyro Bias ($3$).
  - Error states: $\delta\mathbf{x} \in \mathbb{R}^{15}$ with $SO(3)$ error rotation vectors.
- High-rate IMU mechanization integrated with visual PnP pose corrections and altimeter updates.

### Volume V7: Landing Intelligence & Safety Supervisor
- 12-state deterministic finite state machine (`SEARCHING`, `TARGET_ACQUIRED`, `ALIGNING`, `APPROACHING`, `DESCENDING`, `FINAL_APPROACH`, `LANDING_CONFIRMED`, `ABORTING`, `RECOVERY`, `FAULT`, `IDLE`).
- Real-time 3-sigma covariance envelope gating and non-negotiable invariant `ABORT -> never DESCEND`.

### Volume V8: Flight Command Interface
- Rate-limited command authorization gateway ensuring smooth acceleration and velocity limits.
- Complete hardware isolation: no physical actuators, serial ports, or MAVLink interfaces.

### Volume V9: Digital Twin & Scenario Engine
- High-fidelity 6-DoF rigid-body physics simulator with aerodynamic drag, atmospheric wind disturbances, and Gaussian sensor noise models.
- Standardized 12-scenario benchmark suite supporting Monte Carlo statistical validation.

---

## 3. Production Deployment & Reliability Envelope (Phases D1–D9)

### Phase D1: Deployment Foundation
- Multi-stage Docker packaging, non-root user execution, and base service contracts.

### Phase D2: FastAPI REST Backend
- Modular asynchronous routing for health probes, system metadata, and scenario execution.

### Phase D3: Real-Time Telemetry WebSocket
- Low-latency 20 Hz WebSocket streaming with bounded queue backpressure and heartbeat monitoring.

### Phase D4: Hardened Docker Runtime
- Drop-all capabilities (`cap_drop: [ALL]`), `no-new-privileges:true`, and minimal runtime image.

### Phase D5: Production Configuration
- Strict fail-fast Pydantic configuration validation enforcing non-overridable safety flags.

### Phase D6: Cloud Deployment & TLS
- Declarative Infrastructure-as-Code (`render.yaml`) with automated TLS 1.3 certificates.

### Phase D7: Production Observability
- Application-level metrics collector (p50/p95/p99 latency percentiles, error rates), structured single-line JSON logging, and $O(1)$ ring-buffer storage.

### Phase D8: Production Security & Authentication
- Role-based API key management (`READ`, `EXECUTE`, `ADMIN`), constant-time SHA-256 validation, token-bucket rate limiters, and payload size enforcement.

### Phase D9: Release Engineering & Disaster Recovery
- Pre-flight release manifest generator, safe pure-Python Git commit discovery, boot-time startup validator, idempotent graceful shutdown coordinator, deterministic failure classifier, and operational rollback runbook.

---

## 4. Immutable Safety Boundary

```text
hardware_access = false
allow_external = false
allow_network_download = false
hardware_disconnected = true
```

The deployed service functions exclusively as a **Software-in-the-Loop (SITL)** simulation and validation platform. No physical control signals are generated or transmitted.
