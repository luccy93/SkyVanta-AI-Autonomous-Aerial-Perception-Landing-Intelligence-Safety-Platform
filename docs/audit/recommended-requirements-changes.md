# SkyVanta AI — Recommended Requirements Adjustments (V0)

## 1. Requirements Prioritization Tiers (MoSCoW Framework)

```
+---------------------------------------------------------------------------------------------------+
|                                 REQUIREMENTS PRIORITIZATION TIERS                                 |
+---------------------------------------------------------------------------------------------------+
```

### MUST HAVE (Flight-Critical / Core Autonomy)
1. **Calibrated Camera Intrinsic Model**: Matrix $K$ and distortion $D$ for optical metric rectification.
2. **Tri-Tier Perception Fallback**: Level 1 (AprilTag/ArUco), Level 2 (Geometric Contour), Level 3 (YOLO).
3. **PnP 6-DoF Metric Pose Estimation**: Replace heuristic 2D pixel scaling with true physical transformation matrices.
4. **15-State Error-State EKF**: Fusing vision pose, 6-DoF IMU, and 1D LiDAR rangefinder.
5. **Deterministic Safety Supervisor**: Standalone C++ validator with 12 hard invariant rules and direct veto authority over AI commands.
6. **MAVLink 2.0 Offboard Integration**: Communication bridge with PX4 Autopilot.
7. **Simulation-First Verification**: Automated execution across 18 canonical SITL test scenarios.

### SHOULD HAVE (Operational Rigor & Usability)
1. **Lossless Time-Series Flight Logging**: MCAP flight logger with microsecond timestamp synchronization.
2. **Modern Web Ground Control Station**: Next.js/React dashboard with 30 Hz WebSocket telemetry stream and 3D HUD corridor.
3. **TensorRT INT8 Edge Optimization**: Low-SWaP execution on NVIDIA Jetson ($< 15\text{W}$).
4. **Automated CI/CD Benchmark Suite**: Regression testing against 1,000 hard adversarial validation frames.

### NICE TO HAVE (Post-Flight Analytics & Tooling)
1. **RAG-Based AI Debrief Assistant**: Automated natural language flight log diagnostic report generator.
2. **Procedural Scene Generator**: Offline synthetic video generator for rapid computer vision unit testing.
3. **TimescaleDB Telemetry Lake**: Centralized multi-flight time-series query database.

### FUTURE (Advanced Certification & Fleet Scale)
1. **DO-178C / DO-254 Compliance**: Formal commercial aviation software/hardware certification.
2. **Multi-UAV Swarm Deconfliction**: Distributed collaborative landing zone coordination.
3. **Stereo Visual-Inertial SLAM**: Unmapped rough terrain hazard mapping.

---

## 2. Reconciliation of Numerical Performance Targets

> [!IMPORTANT]
> The numerical figures below represent **ENGINEERING DESIGN TARGETS** established in `PROJECT_MASTER_PLAN.md`. They must **NEVER** be cited as currently achieved performance metrics until formally measured in Volume 15 and Volume 18.

| Performance Metric | Design Target Value | Verification Method Required | Status in Codebase |
| :--- | :--- | :--- | :---: |
| **Edge Pipeline Framerate** | $\ge 30\text{ FPS}$ | CUDA event timers on NVIDIA Jetson Orin Nano | **PLANNED TARGET** (Unmeasured) |
| **End-to-End Latency** | $\le 45\text{ ms}$ | Hardware photon-to-MAVLink oscilloscopic test | **PLANNED TARGET** (Unmeasured) |
| **Static Touchdown Accuracy** | $\le 5.0\text{ cm}$ | External optical motion capture (Vicon/OptiTrack) | **PLANNED TARGET** (Unmeasured) |
| **Moving Pad Touchdown Accuracy** | $\le 10.0\text{ cm}$ ($1.5\text{ m/s}$ pad) | Ground-truth laser measurement on dynamic platform | **PLANNED TARGET** (Unmeasured) |
| **Safety Invariant Response Time** | $\le 20\text{ ms}$ | High-precision C++ software execution benchmarks | **PLANNED TARGET** (Unmeasured) |
| **Detection Precision / Recall** | $\ge 95.0\%$ mAP@50 | Automated CI benchmark on labeled test dataset | **PLANNED TARGET** (Unmeasured) |
