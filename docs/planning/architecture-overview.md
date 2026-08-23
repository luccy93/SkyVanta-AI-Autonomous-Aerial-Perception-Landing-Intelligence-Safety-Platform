# SkyVanta AI — System Architecture Overview

## 1. Multi-Tier Distributed Architecture
SkyVanta AI partitions responsibilities across four distinct operational tiers: **Edge Computing Node**, **Ground Control Station (GCS)**, **Simulation Environment**, and **Cloud Analytics & Model Registry**.

```
+-----------------------------------------------------------------------------------------+
|                                    SIMULATION SYSTEM                                     |
|  +------------------------+  +--------------------------+  +--------------------------+  |
|  | Gazebo Harmonic /      |  | PX4 / ArduPilot SITL     |  | Synthetic Sensor & Fault |  |
|  | AirSim Physics Engine  |  | Flight Controller Stack  |  | Injection Engine         |  |
|  +-----------+------------+  +------------+-------------+  +------------+-------------+  |
+--------------|----------------------------|-----------------------------|---------------+
               | Lockstep Virtual Link      | MAVLink / TCP               | Scenario Triggers
               v                            v                             v
+-----------------------------------------------------------------------------------------+
|                                  EDGE COMPUTING NODE (UAV)                              |
|                                                                                         |
|  [ SENSORS ] --->  Camera (CSI/USB)  |  IMU (100Hz)  |  Rangefinder  |  Baro  |  GPS   |
|                           |                 |               |           |        |      |
|                           v                 +---------------+-----------+--------+      |
|                   [ Preprocessing ]                                 |                   |
|                     (Letterbox/CLAHE)                               |                   |
|                           |                                         |                   |
|                           v                                         |                   |
|              +-------------------------+                            |                   |
|              |   PERCEPTION ENGINE     |                            |                   |
|              | - Level 1: AprilTag     |                            |                   |
|              | - Level 2: Pad Detector |                            |                   |
|              | - Level 3: YOLOv8-Nano  |                            |                   |
|              | - Optical Flow / LK     |                            |                   |
|              +------------+------------+                            |                   |
|                           | Detection BBoxes / Corners / Confidence |                   |
|                           v                                         |                   |
|              +-------------------------+                            |                   |
|              |  TRACKING & POSE ENGINE |                            |                   |
|              | - Hungarian Association |                            |                   |
|              | - One Euro Filter       |                            |                   |
|              | - PnP / Homography Pose |                            |                   |
|              +------------+------------+                            |                   |
|                           | Relative Pose T_pad^cam                 |                   |
|                           +-----------------------+                 |                   |
|                                                   |                 |                   |
|                                                   v                 v                   |
|                                     +-----------------------------------+               |
|                                     |    SENSOR FUSION (Error-State EKF)|               |
|                                     | - 15-State Quaternion Kinematics  |               |
|                                     | - Relative 3D Pose & Pad Velocity |               |
|                                     | - Covariance P_est Estimation     |               |
|                                     +-----------------+-----------------+               |
|                                                       | Estimated State & Covariance    |
|                                                       v                                 |
|                                     +-----------------------------------+               |
|                                     |    LANDING INTELLIGENCE (FSM)     |               |
|                                     | - SEARCHING -> ALIGNING -> LAND   |               |
|                                     | - Approach Corridor Trajectory    |               |
|                                     +-----------------+-----------------+               |
|                                                       | Proposed Flight Guidance        |
|                                                       v                                 |
|                                     +-----------------------------------+               |
|                                     |   DETERMINISTIC SAFETY SUPERVISOR |               |
|                                     | - Watchdogs, Covariance Limits    |               |
|                                     | - Velocity & Tilt Envelopes       |               |
|                                     | - Hard Abort / Hold Invariants    |               |
|                                     +-----------------+-----------------+               |
|                                                       | Validated Setpoint / Abort Signal
|                                                       v                                 |
|                                     +-----------------------------------+               |
|                                     |  ROBOTICS INTERFACE (MAVLink 2.0) |               |
|                                     | - SET_POSITION_TARGET_LOCAL_NED   |               |
|                                     | - High-rate MAVLink to Autopilot  |               |
|                                     +-----------------+-----------------+               |
|                                                       | Serial UART / UDP               |
|                                                       v                                 |
|                                        [ Hardware Flight Controller ]                   |
|                                         (PX4 / Cube Orange+ / Pixhawk)                  |
|                                                       |                                 |
+-------------------------------------------------------|---------------------------------+
                                                        |
                         Wi-Fi / 4G / Telemetry Radio   | 20-30 Hz Telemetry & HUD Video
                                                        v
+-----------------------------------------------------------------------------------------+
|                                GROUND CONTROL STATION (GCS)                             |
|                                                                                         |
|  +--------------------+  +--------------------+  +------------------+  +-------------+  |
|  | Real-Time HUD &    |  | FSM State & Safety |  | Telemetry & EKF  |  | AI Mission  |  |
|  | Video Stream View  |  | Override Dashboard |  | Analytics Graph  |  | Debrief Bot |  |
|  +--------------------+  +--------------------+  +------------------+  +-------------+  |
+-------------------------------------------------------|---------------------------------+
                                                        | Flight Logs (MCAP / Parquet)
                                                        v
+-----------------------------------------------------------------------------------------+
|                              CLOUD ANALYTICS & MODEL REGISTRY                           |
|                                                                                         |
|  +--------------------+  +--------------------+  +------------------+  +-------------+  |
|  | Post-Flight Cloud  |  | MLflow Model       |  | Auto-Annotation  |  | Synthetic   |  |
|  | Analytics / S3 Log |  | Registry & Weights |  | & Active Learning|  | Scenario DB |  |
|  +--------------------+  +--------------------+  +------------------+  +-------------+  |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Subsystem Breakdown & Technology Selections

### A. Edge Node Subsystems (Flight-Critical)
* **OS & Runtime**: Ubuntu 22.04 LTS with PREEMPT_RT kernel patches on ARM64 / x86_64.
* **Computer Vision Engine**: C++20 / Python 3.10 with OpenCV 4.8+ (CUDA accelerated), TensorRT 8.6+ / ONNXRuntime for deep learning inference.
* **Perception Models**:
  * *Level 1*: AprilTag 3 (tag36h11) & ArUco (DICT_6X6_250) for millimeter precision in close range ($< 5$m).
  * *Level 2*: Classical contour morphology, geometric invariant moment matching, and quad fitting for standardized landing circles/crosses.
  * *Level 3*: Ultralytics YOLOv8-Nano / YOLOv11-Nano (INT8/FP16 quantized) fine-tuned on aerial drone landing datasets for long-range ($5\text{m} - 40\text{m}$) acquisition.
* **Tracking & Filtering**:
  * Linear/Nonlinear Kalman Filter for 2D bounding box and 3D visual track propagation.
  * One Euro Filter for adaptive high-frequency jitter suppression without phase lag.
  * Perspective-n-Point (PnP) solver (`cv::solvePnP` with `SOLVEPNP_IPPE` for planar targets).
* **Sensor Fusion Core**:
  * Custom 15-state Error-State Extended Kalman Filter (ESEKF) running in C++ at 100 Hz.
  * States: Position (3), Velocity (3), Orientation Quaternion (4), Accel Bias (3), Gyro Bias (3).
* **Deterministic Safety Supervisor**:
  * Zero-allocation, memory-safe C++ execution block. Evaluates hard invariant bounds every 20ms.

### B. Ground Control Station Subsystems (Operator & Monitoring)
* **Frontend**: React 18 / Next.js with TypeScript, TailwindCSS, Lucide Icons, Three.js for 3D trajectory corridor visualization, WebRTC / low-latency H.264 video decoding.
* **Backend Gateway**: FastAPI / Node.js with WebSockets, handling MAVLink telemetry demuxing, mission recording, and event dispatch.
* **AI Debrief Assistant**: Local or hosted LLM agent connected via LangChain/LlamaIndex to indexed flight logs and safety event databases.

### C. Cloud Subsystems (Post-Mission & Continuous Improvement)
* **Data Storage**: MinIO / AWS S3 for raw MCAP logs, video recordings, and sensor dumps.
* **Analytics Database**: TimescaleDB / ClickHouse for time-series telemetry querying.
* **Model Registry**: MLflow for tracking model iterations, INT8 quantization benchmarks, and validation metrics across simulation datasets.
