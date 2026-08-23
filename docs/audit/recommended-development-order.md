# SkyVanta AI — Recommended Implementation Roadmap (V0 to V18)

## 1. Roadmap Phasing Strategy & Sequencing Adjustments

Following the repository audit, the development sequence is structured to prioritize **mathematical correctness and spatial geometry (V1–V5)** before introducing **complex sensor fusion and autopilot closed loops (V6–V10)**, followed by **telemetry and operator tooling (V11–V15)** and finally **hardware deployment (V16–V18)**.

```
+---------------------------------------------------------------------------------------------------+
|                                     THE 4-PHASE DEVELOPMENT ROADMAP                               |
+---------------------------------------------------------------------------------------------------+
| PHASE 1 (V0 - V4): Architectural Foundation, Real Pose Geometry & Staged Perception               |
| -> Eliminate monolithic script; replace heuristic pixel math with calibrated PnP 6-DoF geometry.  |
+---------------------------------------------------------------------------------------------------+
| PHASE 2 (V5 - V10): Spatial Localization, Sensor Fusion, Landing Intelligence & Safety            |
| -> Implement 15-State ESEKF, 12-State FSM, Deterministic Safety Supervisor, and PX4 SITL MAVLink. |
+---------------------------------------------------------------------------------------------------+
| PHASE 3 (V11 - V15): Telemetry Streaming, Ground Control Station & Model Evaluation               |
| -> Build WebSocket gateway, Next.js GCS dashboard, automated CI/CD benchmark scorecard.          |
+---------------------------------------------------------------------------------------------------+
| PHASE 4 (V16 - V18): Hardware-in-the-Loop, Physical Integration & Moving-Pad Demonstration        |
| -> Jetson bench validation, tethered flight cage testing, autonomous landing on dynamic target.   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Detailed Volume Specifications

### Phase 1: Foundation, Perception & Geometry
* **Volume 0 (V0) — Master Plan Reconciliation & Repository Audit** *(Current Phase)*:
  * *Objective*: Complete exhaustive codebase audit, gap analysis, and implementation readiness baseline.
  * *Exit Gate*: Audit documentation approved; zero unverified claims.
* **Volume 1 (V1) — Architecture Foundation & Build System**:
  * *Objective*: Refactor monolithic `main.py` into modular package `skyvanta/` (`perception`, `tracking`, `geometry`, `hud`). Add `pyproject.toml`, `CMakeLists.txt`, and `pytest` framework.
  * *Exit Gate*: Clean automated test runner with 100% passing baseline tests.
* **Volume 2 (V2) — Perception Pipeline (YOLOv8 & Classical Contour)**:
  * *Objective*: Fine-tune YOLOv8-Nano on aerial drone/pad datasets; optimize Level 2 contour quad matching and CLAHE preprocessing.
  * *Exit Gate*: $\ge 90\%$ detection precision on validation set without COCO proxy class hacks.
* **Volume 3 (V3) — Multi-Target Tracking Engine**:
  * *Objective*: Implement Hungarian data association matcher and multi-target track lifecycle management.
  * *Exit Gate*: Zero ID switches across standard 300-frame video benchmark.
* **Volume 4 (V4) — Staged Landing Pad Architecture & PnP Pose Solver**:
  * *Objective*: Integrate AprilTag 3 (tag36h11) and ArUco detectors; implement `cv2.solvePnP` (`SOLVEPNP_IPPE`) using calibrated camera matrix $K$.
  * *Exit Gate*: Accurate 6-DoF metric pose estimation ($T_{pad}^{cam}$) validated on known planar targets.

### Phase 2: State Estimation, Safety & Robotics
* **Volume 5 (V5) — Spatial Coordinate Localization & Transformation Engine**:
  * *Objective*: Implement rigorous transformations between Camera ($C$), Body ($B$), World ($W$), and Pad ($P$) frames.
* **Volume 6 (V6) — Multi-Sensor Fusion Core (15-State Error-State EKF)**:
  * *Objective*: Develop 15-state quaternion ESEKF fusing Camera PnP pose, 6-DoF IMU kinematics, and 1D LiDAR rangefinder.
* **Volume 7 (V7) — Landing Intelligence Engine (12-State FSM & Glide-Slope)**:
  * *Objective*: Implement deterministic 12-state flight FSM and exponential descent velocity profiler.
* **Volume 8 (V8) — Deterministic Safety Supervisor & Invariant Watchdogs**:
  * *Objective*: Build standalone C++ safety validator monitoring 12 hard invariants and fail-safe triggers (`HOLD`, `ABORT`, `RTL`).
* **Volume 9 (V9) — Gazebo Harmonic & PX4 SITL Simulation Harness**:
  * *Objective*: Create Gazebo simulation environment with camera, IMU, LiDAR plugins, moving landing pad, and 18 automated scenario scripts.
* **Volume 10 (V10) — Robotics & MAVLink 2.0 Interface**:
  * *Objective*: Build asynchronous MAVLink communication bridge connecting SkyVanta perception to PX4 Autopilot in Offboard mode.

### Phase 3: Telemetry, Ground Station & Edge Optimization
* **Volume 11 (V11) — Telemetry Streaming & Lossless Logging**:
  * *Objective*: Protobuf/WebSocket 30 Hz streaming gateway and MCAP time-series flight logger.
* **Volume 12 (V12) — Ground Control Station (GCS) Dashboard**:
  * *Objective*: Next.js 14, React 18, TailwindCSS, Three.js 3D perspective corridor HUD, and WebRTC live video.
* **Volume 13 (V13) — Post-Flight AI Assistant & Debriefing Tool**:
  * *Objective*: Non-flight-critical RAG diagnostic assistant querying TimescaleDB flight logs.
* **Volume 14 (V14) — Edge AI Optimization & TensorRT INT8 Deployment**:
  * *Objective*: Quantize perception models to TensorRT INT8 on NVIDIA Jetson Orin Nano ($< 15\text{ms}$ latency).
* **Volume 15 (V15) — Model Evaluation & CI/CD Regression Scorecards**:
  * *Objective*: Automated GitHub Actions regression test suite against 1,000 hard adversarial test frames.

### Phase 4: Validation & Physical Prototyping
* **Volume 16 (V16) — Hardware-in-the-Loop (HIL) Integration**:
  * *Objective*: Connect physical Jetson Orin Nano to physical Pixhawk flight controller over UART serial on a static test bench.
* **Volume 17 (V17) — Tethered Airframe & Flight Cage Prototyping**:
  * *Objective*: Outdoor cage flight testing with active tether line and safety pilot RC override.
* **Volume 18 (V18) — Final Verification & Dynamic Moving-Pad Demonstration**:
  * *Objective*: Full autonomous approach and touchdown on a moving landing platform ($1.5\text{ m/s}$) with active fault injection.
