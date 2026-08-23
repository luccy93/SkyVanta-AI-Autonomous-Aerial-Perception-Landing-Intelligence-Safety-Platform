# SkyVanta AI — Over-Engineering & Complexity Analysis (V0)

## 1. Architectural Phasing & Deferral Framework

To prevent project paralysis, premature optimization, and wasted engineering cycles, the planned subsystems in `PROJECT_MASTER_PLAN.md` are evaluated and categorized into chronological implementation tiers: **EARLY**, **MIDDLE**, **LATE**, **OPTIONAL**, and **FUTURE**.

```
+---------------------------------------------------------------------------------------------------+
|                                 IMPLEMENTATION COMPLEXITY PHASING                                 |
+---------------------------------------------------------------------------------------------------+
| EARLY (V1 - V5): Core Vision, Pose Geometry, Package Structure, Simulation Foundation            |
+---------------------------------------------------------------------------------------------------+
| MIDDLE (V6 - V10): Sensor Fusion (ESEKF), Landing FSM, Safety Supervisor, MAVLink SITL            |
+---------------------------------------------------------------------------------------------------+
| LATE (V11 - V15): Web Ground Station, Telemetry Lake, Model Quantization, CI Benchmarks           |
+---------------------------------------------------------------------------------------------------+
| OPTIONAL / FUTURE (V16 - V18+): RAG AI Assistant, Multi-Node Kubernetes, Physical Flight Testing |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Component Phasing Evaluation

| System Component | Planned Capability in Master Plan | Phasing Category | Technical Rationale for Phasing |
| :--- | :--- | :---: | :--- |
| **Package Modularization** | Clean Python/C++ package layout, CMake, pyproject.toml | **EARLY (V1)** | Mandatory foundation. Continuing with a single monolithic `main.py` blocks unit testing and modular development. |
| **AprilTag & ArUco Pose** | AprilTag 3 + SolvePnP planar pose estimation | **EARLY (V4)** | Replaces heuristic pixel math with true physical 6-DoF geometry early in the pipeline. |
| **15-State Error EKF** | Full quaternion-based IMU+Vision+LiDAR state estimator | **MIDDLE (V6)** | Essential for real flight dynamics, but should be built in simulation after 6-DoF vision pose is validated. |
| **Safety Supervisor** | Independent C++ deterministic invariant validator | **MIDDLE (V8)** | Must be developed and stress-tested in simulation before any flight controller commands are enabled. |
| **MAVLink SITL Bridge** | PX4 SITL / MAVLink 2.0 serial integration | **MIDDLE (V10)** | Closed-loop simulation verification requires autopilot bridge; must follow state estimation. |
| **WebRTC & 3D GCS Web UI** | React 18, Next.js, Three.js 3D perspective dashboard | **LATE (V12)** | A rich web UI is valuable for operators, but does not affect the core autonomous perception and safety loops. |
| **TensorRT INT8 Quantization** | Full post-training INT8 quantization on Jetson | **LATE (V14)** | PyTorch/ONNX FP16 is sufficient for development; INT8 calibration should be done once models stabilize. |
| **AI Debrief Assistant (RAG)**| LLM agent connected to ChromaDB & TimescaleDB | **OPTIONAL (V13)** | Non-flight-critical auxiliary feature. Should not consume core robotics engineering bandwidth early on. |
| **Physical Airframe & HIL** | Jetson + Cube Orange+ on carbon fiber airframe | **FUTURE (V16-V18)** | Physical procurement and flight testing must wait until all 18 simulation scenarios pass with 100% regression. |
| **Cloud Microservices** | MinIO S3, ClickHouse, Docker Swarm / K8s | **FUTURE** | Unnecessary overhead for early desktop and single-airframe edge testing. Simple local SQLite/MCAP logging is superior. |
