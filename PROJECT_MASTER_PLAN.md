# SkyVanta AI — Master Project Plan
## Autonomous Aerial Perception, Landing Intelligence & Safety Platform

---

> **DOCUMENT CONTROL & GOVERNANCE**
> * **Project Name**: SkyVanta AI
> * **Document Title**: Master Project Plan (Single Source of Truth)
> * **Author / Role**: Principal AI & Robotics Architect (SkyVanta-AI / Devendraprasad)
> * **Status**: APPROVED ARCHITECTURAL SPECIFICATION (PLANNING PHASE)
> * **Target Domain**: Autonomous Aerial Robotics, Computer Vision, Edge AI, Safety-Critical Systems

---

## 1. Executive Summary

### 1.1 What is SkyVanta AI?
**SkyVanta AI** is an industrial-grade, real-time aerial perception, state estimation, and landing-intelligence platform engineered for Unmanned Aerial Vehicles (UAVs). It provides a deterministic, vision-guided autonomous landing capability across unmapped, GPS-degraded, dynamically moving, and visually adverse environments.

### 1.2 What Problem Does It Solve?
Terminal landing represents over 60% of all drone accidents and hull losses. Modern commercial and tactical drones depend heavily on satellite navigation (GNSS/RTK) and simple altitude sensors. In GPS-denied environments (urban canyons, maritime vessels, dense industrial scaffolding, electronic countermeasure zones), standard drones drift, lose reference, or crash during terminal descent. Furthermore, existing AI vision prototypes are probabilistic and lack formal safety supervisors, making them prone to erratic behavior during visual occlusion, motion blur, or model misdetections.

### 1.3 Target Audience & Stakeholders
* **Autonomous Cargo & Logistics Fleets**: Demanding sub-5cm autonomous recovery onto automated charging stations and cargo lockers.
* **Offshore Energy & Maritime Operators**: Requiring robust touchdown on moving ship decks and vibrating offshore platforms under wave-induced heave, roll, and pitch.
* **Defense & Emergency First Responders**: Operating in contested, GPS-denied forward operating environments.
* **Robotics Research & OEM Developers**: Needing a standardized, modular perception and safety layer that interfaces cleanly with PX4 and ArduPilot via MAVLink.

### 1.4 Technical Significance
SkyVanta AI advances the state-of-the-art by combining:
1. **Tri-Tier Perception**: Staged fallback across fiducial markers (Level 1: AprilTag/ArUco), geometric template matching (Level 2), and deep neural object detectors (Level 3: YOLOv8/v11 Nano).
2. **Deterministic Dual-Channel Safety**: Strict architectural decoupling where a deterministic C++ safety supervisor validates all AI recommendations against kinematic envelopes before issuing flight commands.
3. **15-State Error-State Extended Kalman Filter (ESEKF)**: Tightly fusing visual relative pose, 6-DoF IMU kinematics, 1D laser rangefinder distance, and landing pad dynamic velocity at 100 Hz.
4. **Progressive Verification Lifecycle**: Rigorous progression from software simulation and PX4 SITL to Hardware-in-the-Loop (HIL) and tethered flight testing.

### 1.5 The Final Demonstration Vision
The culmination of the project will demonstrate a fully autonomous, vision-guided approach and touchdown from 30 meters altitude onto a dynamically moving landing pad under simulated GPS-denied conditions, surviving active fault injection (transient visual occlusion, sudden crosswind gusts, sensor dropouts) with zero safety violations and sub-5cm touchdown error.

---

## 2. Problem Statement

### 2.1 The Physics & Perception Challenges of Terminal Drone Landing
Autonomous drone recovery is an inherently coupled, non-linear control and estimation problem compounded by severe sensory disturbances:

```
+-----------------------------------------------------------------------------------------+
|                                ENVIRONMENTAL & PHYSICAL DISTURBANCES                     |
|                                                                                         |
|  [ Camera Ego-Motion ]      [ Atmospheric Disturbances ]      [ Surface & Lighting ]    |
|  * Rapid angular rates      * Wind shear & gusts              * Direct solar glare      |
|  * High-frequency vibration * Ground-effect rotor wash        * Dynamic shadow sweep    |
|  * Severe motion blur       * Thermal updrafts                * Low contrast textures   |
|                                                                                         |
|  [ Dynamic Platform ]       [ Sensor Degeneracy ]             [ System Latency ]        |
|  * Wave heave & roll (ship) * GPS multi-path / jamming        * Image sensor exposure   |
|  * Constant velocity motion * Rangefinder specular dropout   * TensorRT inference lag  |
|  * Accelerating turn rates  * Barometric ground pressure surge* MAVLink serial transport|
+-----------------------------------------------------------------------------------------+
```

### 2.2 Deep Dive into Failure Modes
1. **Monocular Scale Ambiguity**: Without active range sensing or geometric ground-truth fiducials, single-camera vision cannot distinguish between a small pad close up and a large pad far away.
2. **Ground-Effect Turbulence**: Below 0.5m altitude, drone rotor downwash reflects off the ground, inducing chaotic high-frequency attitude oscillations and kicking up dust that obscures the camera.
3. **Moving Landing Pad Kinematics**: When landing on a moving vessel or ground vehicle, the target possesses its own independent 6-DoF velocity and acceleration that must be tracked and synchronized in real time.
4. **The Latency-Bandwidth Bottleneck**: High-resolution image processing introduces pipeline latency. If perception lag exceeds 50ms, feedback control becomes unstable during high-speed terminal descent.

---

## 3. Project Objectives

```
+---------------------------------------------------------------------------------------+
|                               PROJECT OBJECTIVES ROADMAP                              |
+---------------------------------------------------------------------------------------+
|  PRIMARY OBJECTIVES (Core Autonomous Flight-Critical Engine)                          |
|  * PO-1: Sub-5cm landing accuracy on static target under nominal conditions.          |
|  * PO-2: Sub-10cm landing accuracy on moving target (up to 2.0 m/s linear velocity).  |
|  * PO-3: >= 30 FPS edge inference & state estimation at <= 45ms end-to-end latency.  |
|  * PO-4: 100% deterministic fail-safe trigger during sensor loss or invariant breach. |
|  * PO-5: Zero dependency on global GPS during terminal descent (vision/inertial only).|
+---------------------------------------------------------------------------------------+
|  SECONDARY OBJECTIVES (Operational Tooling & User Experience)                         |
|  * SO-1: Web-based real-time Ground Control Station with 3D corridor HUD stream.      |
|  * SO-2: Comprehensive 18-scenario automated SITL simulation regression suite.       |
|  * SO-3: Post-flight AI Debrief Assistant indexing flight logs and safety events.     |
|  * SO-4: Complete microsecond-synchronized flight data logging (MCAP / TimescaleDB).  |
+---------------------------------------------------------------------------------------+
|  FUTURE OBJECTIVES (Post-V18 Certification & Multi-Agent Operations)                  |
|  * FO-1: DO-178C / DO-254 commercial aerospace certification pathway.                 |
|  * FO-2: Multi-drone swarm cooperative landing coordination on shared landing zones.  |
|  * FO-3: Stereo visual-inertial SLAM for uncooperative terrain hazard mapping.        |
+---------------------------------------------------------------------------------------+
```

---

## 4. Project Scope

```
+---------------------------------------------------+----------------------------------------------------+
| IN SCOPE                                          | OUT OF SCOPE (INITIAL PHASES)                      |
+---------------------------------------------------+----------------------------------------------------+
| 1. Monocular & Stereo edge vision processing      | 1. Formal DO-178C / DO-254 FAA airworthiness cert  |
| 2. Tri-tier target & landing pad detection        | 2. Commercial passenger / air-taxi flight ops      |
| 3. Kalman & One Euro trajectory smoothing         | 3. Writing custom low-level motor PID mixers       |
| 4. Perspective-n-Point (PnP) 6-DoF pose solver    | 4. Unsupervised BVLOS flight over public crowds    |
| 5. 15-state Error-State Extended Kalman Filter    | 5. Latency-critical cloud-based flight control     |
| 6. Deterministic safety supervisor & invariants   | 6. Custom proprietary flight controller silicon    |
| 7. PX4 / ArduPilot MAVLink 2.0 interface          | 7. Unverified physical outdoor flights without RC  |
| 8. Gazebo Harmonic / AirSim SITL & HIL simulation |                                                    |
| 9. Web Ground Control Station & AI Debrief Bot    |                                                    |
| 10. Low-SWaP Edge deployment (NVIDIA Jetson / Pi) |                                                    |
+---------------------------------------------------+----------------------------------------------------+
```

---

## 5. System Capabilities (A through T)

| Cap ID | Capability Name | Purpose | Inputs | Processing Engine | Outputs | Dependencies | Success Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **A** | **Drone Detection** | Detect peer UAVs / obstacles in airspace | Raw Camera Frame ($1280 \times 720$) | YOLOv8-Nano TensorRT | 2D BBoxes, Class ID, Confidence | Preprocessing | $\ge 90\%$ Precision at $> 15\text{m}$ |
| **B** | **Landing-Pad Detection** | Identify landing pad structure from altitude | Raw Camera Frame ($1280 \times 720$) | YOLOv8 + Contour Quad Matcher | BBox, Center Pixel $(u, v)$, Label | Preprocessing | $\ge 95\%$ Recall across $2\text{m} - 35\text{m}$ |
| **C** | **Object Tracking** | Maintain persistent target ID across frames | Detection BBoxes, Frame $t$ | Hungarian Matcher + 2D Kalman | Active Track ID, Velocity vector | Cap B | 0 ID switches across 300-frame run |
| **D** | **Motion Estimation** | Quantify camera ego-motion & surface flow | Consecutive Grayscale Frames | Sparse Lucas-Kanade / Farneback | 2D Velocity Flow Vectors $(\dot{u}, \dot{v})$ | Frame Capture | $< 5\%$ drift over 10s hover |
| **E** | **Camera Calibration** | Remove lens distortion & find intrinsics | Checkerboard / Charuco images | OpenCV Camera Calibrator | Matrix $K$, Distortion coefficients $D$| Offline tooling | Reprojection error $< 0.25$ px |
| **F** | **Relative Localization** | Compute 6-DoF vector from camera to pad | Target Keypoints, Matrix $K$ | SolvePnP (IPPE Planar Solver) | Relative Pose $T_{pad}^{cam} = [R \vert t]$ | Cap B, Cap E | $< 3\text{cm}$ positional error at $5\text{m}$ |
| **G** | **Sensor Fusion** | Fuse vision pose, IMU, and LiDAR range | Vision Pose, IMU (100Hz), LiDAR | 15-State Error-State EKF | Estimated Pose, Velocity, Covariance | Cap F, IMU, LiDAR| Zero divergence; $< 2\text{cm}$ RMSE |
| **H** | **Trajectory Estimation**| Predict landing pad & drone future path | Filtered State History | Kinematic Extrapolator + One Euro | 3D Trajectory Spline ($t + 2\text{s}$) | Cap G | Prediction error $< 0.1\text{m}$ at $1\text{s}$ |
| **I** | **Landing Alignment** | Compute lateral offset & heading error | State Vector $X_k$, Target Heading | Geometric Error Projection | $\Delta x, \Delta y, \Delta z, \Delta \psi$ alignment | Cap G | Heading aligned within $\pm 3^\circ$ |
| **J** | **Approach Estimation** | Calculate glide slope & descent rate | Relative Position & Velocity | Optimal Velocity Profiler | Commanded Setpoint $(\vec{v}_{cmd})$ | Cap I | Smooth exponential descent curve |
| **K** | **Landing State Machine**| Govern flight operational states | Safety signals, Alignment metrics | Deterministic 12-State FSM | Active State (e.g., `APPROACHING`) | Cap G, Cap J | 0 invalid state transitions |
| **L** | **Safety Supervisor** | Validate flight envelope & enforce aborts | State Vector, Sensor Health, Watchdog| Hard Invariant Rule Evaluator | Override Signal (`ALLOW`/`HOLD`/`ABORT`)| Cap K, All sensors| Evaluates in $< 1\text{ms}$; 100% fail-safe |
| **M** | **Telemetry** | Package & broadcast high-rate flight data | Fused State, Invariants, HUD stats | Protobuf / JSON Serializer | Telemetry Stream (30 Hz WebSocket) | Cap G, Cap L | $< 15\text{ms}$ network serialization |
| **N** | **Simulation** | Validate closed-loop flight in virtual world | Virtual Actuator Commands | Gazebo Harmonic / PX4 SITL | Virtual Sensors (Camera, IMU, LiDAR)| Host PC GPU | Lockstep physics execution at 60 FPS |
| **O** | **Ground Dashboard** | Render HUD, 3D corridor, and flight graphs | Telemetry Stream, Video Stream | React, Three.js, WebRTC | Interactive GCS Web UI | Cap M, Network | 60 FPS rendering, $< 100\text{ms}$ glass-to-glass |
| **P** | **Data Recording** | Persist microsecond-accurate mission logs | Raw sensor frames, States, Events | MCAP / Parquet / TimescaleDB Logger | Mission Log Files (.mcap) | Cap G, Cap L | 0 dropped frames; lossless sync |
| **Q** | **Analytics** | Compute post-flight metrics & KPIs | Mission Log Database | Python Pandas / Polars Analytics | Summary Report (Touchdown error, etc.)| Cap P | Automated report generation $< 5\text{s}$ |
| **R** | **AI Assistant** | Natural language flight debriefing | Flight Log Vector DB, User Prompt | LLM Agent (LangChain / LlamaIndex) | Structured Diagnostic Debriefing | Cap Q | Factual grounding (0 hallucinations) |
| **S** | **Model Evaluation** | Benchmark detection & tracking models | Labeled Test Benchmark Dataset | Precision-Recall & Latency Evaluator| Benchmark Scorecard & ROC curves | Cap B, Model Reg | Automated CI/CD regression gating |
| **T** | **Edge Deployment** | Optimize & execute models on edge SoC | ONNX Models, CUDA Runtime | TensorRT INT8 Quantizer & Engine | Production Binary (.engine) | Cap B, Jetson HW | Sustained 30+ FPS at $< 15\text{W}$ power |

---

## 6. End-to-End System Data Flow

```
+-----------------------------------------------------------------------------------------+
|                                END-TO-END DATA PIPELINE                                 |
+-----------------------------------------------------------------------------------------+

  [ CAMERA SENSOR ] (1280x720 @ 30/60 FPS, CSI/USB)
         | Raw BGR Frame (Timestamped uSec)
         v
  [ PREPROCESSING ] -------------------------------------------------+
         | Undistorted, Normalized, Letterboxed Frame                |
         |                                                           |
         v                                                           v
  [ PERCEPTION ENGINE ]                                     [ OPTICAL FLOW ENGINE ]
    - Level 1: AprilTag / ArUco                               - Sparse Lucas-Kanade
    - Level 2: Classical Geometric Contour                     - Visual Odometry Delta
    - Level 3: YOLOv8-Nano TensorRT                                  |
         | Bounding Boxes, Keypoints, Confidence Score               |
         v                                                           |
  [ TRACKING & PNP POSE SOLVER ]                                     |
    - Hungarian Data Association                                     |
    - SolvePnP Pose Estimation -> T_pad^cam                          |
         | Relative 6-DoF Vector [x, y, z, roll, pitch, yaw]          |
         +-----------------------------+                             |
                                       |                             |
  [ AUXILIARY HARDWARE SENSORS ]       |                             |
    - 6-DoF IMU (100 Hz Accel/Gyro) ---+                             |
    - 1D LiDAR Altimeter (50 Hz) ------+                             |
    - Barometer / GNSS ----------------+                             |
                                       |                             |
                                       v                             v
                       +-----------------------------------------------+
                       |        ERROR-STATE KALMAN FILTER (ESEKF)      |
                       | - State: Pos (3), Vel (3), Quat (4), Biases(6)|
                       | - Target Dynamic Velocity (v_pad_x, y)        |
                       | - Covariance P_est & Innovation Residuals     |
                       +-----------------------+-----------------------+
                                               | Fused State Vector & Covariance (100 Hz)
                                               v
                       +-----------------------------------------------+
                       |        LANDING INTELLIGENCE ENGINE (FSM)      |
                       | - Dynamic Approach Corridor Calculation       |
                       | - Glide-Slope & Exponential Descent Profiling |
                       | - Trajectory Guidance Vector Generation       |
                       +-----------------------+-----------------------+
                                               | Proposed Setpoint (Pos/Vel)
                                               v
                       +-----------------------------------------------+
                       |         DETERMINISTIC SAFETY SUPERVISOR       |
                       | - 12 Hard Invariant Rule Watchdogs (50 Hz)    |
                       | - Velocity, Tilt, Covariance & Timeout Limits |
                       +-----------------------+-----------------------+
                                               |
                       +-----------------------+-----------------------+
                       |                                               |
              [ Invariants PASSED ]                         [ Invariant VIOLATED ]
                       |                                               |
                       v                                               v
  [ MAVLINK 2.0 PROTOCOL ADAPTER ]                    [ FAIL-SAFE OVERRIDE ENGINE ]
    - SET_POSITION_TARGET_LOCAL_NED                     - Command HOLD (Zero Vel Hover)
    - High-Rate MAVLink to Autopilot                    - Command CLIMB ABORT (15m AGL)
         | Serial UART (921600 baud)                         | Direct Override Packet
         +-----------------------------+---------------------+
                                       |
                                       v
                     [ HARDWARE FLIGHT CONTROLLER (PX4) ]
                       - Low-Level Attitude & Motor Control
                       - Direct ESC / Actuator PWM Signaling
                                       |
                                       | High-Rate Flight Telemetry
                                       v
                     [ TELEMETRY DEMUX & STREAM GATEWAY ]
                                       | WebSockets / gRPC (30 Hz)
                                       v
                     [ GROUND CONTROL STATION (GCS) WEB UI ]
                       - Real-Time HUD Overlay & Video Stream
                       - 3D Approach Corridor Visualizer
                       - Interactive Safety Override Console
```

---

## 7. High-Level Architecture

SkyVanta AI adopts a strict **Edge-Centric, Cloud-Decoupled Distributed Architecture**:

```
+-----------------------------------------------------------------------------------------+
| 1. EDGE SYSTEM (Flight-Critical — Zero Cloud Dependency — Hard Real-Time)               |
|                                                                                         |
|  +--------------------+  +--------------------+  +--------------------+  +-----------+  |
|  | Perception Engine  |  | 15-State ESEKF     |  | Landing FSM &      |  | Safety    |  |
|  | (YOLO / AprilTag)  |  | State Estimator    |  | Guidance Generator |  | Supervisor|  |
|  +--------------------+  +--------------------+  +--------------------+  +-----------+  |
|            ^                       ^                       ^                   ^        |
|            +-----------------------+-----------------------+-------------------+        |
|                                    | Inter-Process Comm (Shared Memory / ZeroMQ)        |
|                                    v                                                    |
|                      +--------------------------+                                       |
|                      | MAVLink 2.0 Serial Layer | <---> Physical Flight Controller (PX4)|
|                      +--------------------------+                                       |
+-----------------------------------------------------------------------------------------+
                                         |
                                         | Telemetry Stream (Wi-Fi / 915MHz Radio / LTE)
                                         v
+-----------------------------------------------------------------------------------------+
| 2. GROUND SYSTEM (Operator Station — Low Latency Monitoring & Manual Override)          |
|                                                                                         |
|  +--------------------+  +--------------------+  +--------------------+  +-----------+  |
|  | Web Video Stream   |  | Real-Time HUD      |  | 3D Trajectory      |  | Safety    |  |
|  | (WebRTC / H.264)   |  | Telemetry Dashboard|  | Corridor Viewer    |  | Override  |  |
|  +--------------------+  +--------------------+  +--------------------+  +-----------+  |
|            ^                       ^                       ^                   ^        |
|            +-----------------------+-----------------------+-------------------+        |
|                                    | React 18 / Next.js / TailwindCSS GCS UI            |
|                                    v                                                    |
|                      +--------------------------+                                       |
|                      | FastAPI / Node.js Gateway| <---> Local Flight Log Storage (MCAP) |
|                      +--------------------------+                                       |
+-----------------------------------------------------------------------------------------+
                                         |
                                         | Asynchronous Post-Flight Batch Sync
                                         v
+-----------------------------------------------------------------------------------------+
| 3. CLOUD SYSTEM (Post-Mission Analytics & AI Ops — Non-Flight-Critical)                 |
|                                                                                         |
|  +--------------------+  +--------------------+  +--------------------+  +-----------+  |
|  | S3 / MinIO Flight  |  | TimescaleDB Fleet  |  | MLflow Model       |  | AI Mission|  |
|  | Log Lake (MCAP)    |  | Telemetry Store    |  | Registry (INT8)    |  | DebriefBot|  |
|  +--------------------+  +--------------------+  +--------------------+  +-----------+  |
+-----------------------------------------------------------------------------------------+
```

---

## 8. Computer Vision Architecture

### 8.1 Algorithm Comparison & Justification Matrix

| Component | Candidate Algorithms | Recommended Selection | Architectural Justification | Limitations & Fallback Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Object Detector** | • YOLOv8-Nano<br>• YOLOv11-Nano<br>• SSD-MobileNet v3<br>• Faster R-CNN | **YOLOv8-Nano (TensorRT INT8)** | Best-in-class latency/accuracy trade-off on edge SoCs ($12\text{ms}$ on Orin Nano); superior small-target feature pyramid. | Struggles under extreme blur. Fallback to Level 2 contour analysis. |
| **Fiducial Detector** | • AprilTag 3 (tag36h11)<br>• ArUco (DICT_6X6)<br>• STag | **AprilTag 3 + ArUco Dual Engine** | AprilTag provides lowest false-positive rate at steep angles; ArUco provides ultra-fast decoding at close range. | Range limited by camera resolution. Transition to Level 3 at $> 10\text{m}$. |
| **Feature Tracking** | • Lucas-Kanade (LK)<br>• ORB Features<br>• SuperPoint / SuperGlue | **Sparse Lucas-Kanade with Pyramids** | Deterministic low CPU overhead ($< 3\text{ms}$); excellent differential motion tracking between consecutive frames. | Sensitive to large lighting steps. Mitigated via CLAHE preprocessing. |
| **Pose Estimation** | • SolvePnP (IPPE)<br>• SolvePnP (RANSAC)<br>• Homography SVD | **SolvePnP (SOLVEPNP_IPPE)** | Infinitesimal Plane-based Pose Estimation is mathematically optimal for planar landing targets, eliminating dual-pose ambiguity. | Requires at least 4 coplanar keypoints. Fallback to center-ray projection. |
| **Image Preprocessing**| • Simple Resize<br>• CLAHE + Letterbox<br>• Bilateral Filtering | **Letterbox + CLAHE (CUDA)** | Contrast Limited Adaptive Histogram Equalization recovers pad edges under intense shadows and direct solar washout. | Slight compute overhead ($1.2\text{ms}$ on GPU). Enabled dynamically. |

---

## 9. AI/ML Architecture & MLOps Pipeline

```
+-----------------------------------------------------------------------------------------+
|                                    MLOPS LIFECYCLE                                      |
+-----------------------------------------------------------------------------------------+

  [ DATA COLLECTION ] ---> Public Datasets (VisDrone) + Synthetic Gazebo Frames + Field Flight Logs
         |
         v
  [ AUTO-ANNOTATION ] ---> Zero-Shot SAM (Segment Anything) + AprilTag Ground-Truth Extractor
         |
         v
  [ AUGMENTATION ] ------> Physics-Aware Blur, Sun Flare, Sensor Noise, Perspective Warping
         |
         v
  [ MODEL TRAINING ] ----> PyTorch / Ultralytics YOLOv8-Nano Fine-Tuning (Distributed GPU)
         |
         v
  [ QUANTIZATION ] ------> TensorRT INT8 Calibration (Post-Training Quantization with Entropy Calibrator)
         |
         v
  [ BENCHMARK GATING ] --> CI/CD Evaluator: Must achieve >= 92% mAP@50 and <= 15ms latency
         |
         +--> [ PASSED ] --> Deploy to Edge Device via MLflow Model Registry
         |
         +--> [ FAILED ] --> Flag Hard Samples, Trigger Active Learning Retraining Loop
```

---

## 10. Tracking Architecture

### 10.1 Tracking Lifecycle & State Transition Graph
Multi-target tracking resolves temporal association between frame detections and active flight tracks:

```
                  +---------------+
                  |  DETECTION    |
                  +-------+-------+
                          |
                          v
               +---------------------+
               | Hungarian Matcher   | <--- Mahalanobis & IoU Distance Metric
               +----------+----------+
                          |
         +----------------+----------------+
         |                                 |
[ Match Found ]                   [ Unmatched Detection ]
         |                                 |
         v                                 v
+-----------------+               +-----------------+
| Update 2D EKF   |               | Initialize Tentative
| State & Trail   |               | Track (Age = 1) |
+--------+--------+               +--------+--------+
         |                                 |
         | Hits >= 5 Frames                | Hits >= 5 Frames
         v                                 v
+-----------------+               +-----------------+
|   CONFIRMED     |               |   CONFIRMED     |
|   ACTIVE TRACK  |               |   ACTIVE TRACK  |
+--------+--------+               +-----------------+
         |
[ Missed Detection (0 < Miss <= 30 frames) ]
         |
         v
+-----------------+
| PREDICTED /     | ---> (IMU Dead-Reckoning & Kalman Propagation)
| COASTING STATE  |
+--------+--------+
         |
         | Miss > 30 frames (1.0 second)
         v
+-----------------+
|  TERMINATE &    | ---> (Trigger Safety Supervisor `HOLD` Sequence)
|  DELETE TRACK   |
+-----------------+
```

---

## 11. Landing-Pad Architecture: Tri-Tier Staged Perception

```
+-----------------------------------------------------------------------------------------+
| LEVEL 3: Deep Neural Detector (Long Range: 15m to 40m)                                  |
| * Algorithm: YOLOv8-Nano (Trained on Airframes & Landing Pads)                          |
| * Function: Global landing zone localization in camera FOV; guides initial approach.    |
+-----------------------------------------------------------------------------------------+
                                         | Altitude < 15m & Pad In Center FOV
                                         v
+-----------------------------------------------------------------------------------------+
| LEVEL 2: Geometric & Contour Perception (Mid Range: 3m to 15m)                          |
| * Algorithm: Adaptive Thresholding, Ellipse Fitting, Concentric Ring Symmetry Matching  |
| * Function: Robust cross/circle feature extraction invariant to scale and rotation.     |
+-----------------------------------------------------------------------------------------+
                                         | Altitude < 4m & Fiducial Pattern Resolved
                                         v
+-----------------------------------------------------------------------------------------+
| LEVEL 1: High-Precision Fiducial Marker (Close Range: 0.1m to 4m)                       |
| * Algorithm: AprilTag 3 (tag36h11) / ArUco 6x6 Nested Multi-Resolution Matrix           |
| * Function: Sub-millimeter corner extraction; exact 6-DoF metric pose for touchdown.   |
+-----------------------------------------------------------------------------------------+
```

---

## 12. Localization & Coordinate Transformations

### 12.1 Standardized Coordinate Frames
1. **Camera Optical Frame ($C$)**: $X$-right, $Y$-down, $Z$-forward along the optical axis.
2. **Drone Body Frame ($B$)**: $X$-forward, $Y$-right, $Z$-down (Standard Aerospace Body NED).
3. **Local World Navigation Frame ($W$)**: $X$-North, $Y$-East, $Z$-Down (Local NED tangent plane).
4. **Landing Pad Target Frame ($P$)**: $X$-forward along pad major axis, $Y$-right, $Z$-normal pointing into pad surface.

```
Transformation Chain:
T_pad^W = T_body^W * T_camera^body * T_pad^camera
```

---

## 13. Sensor Architecture & Abstraction Layer

| Sensor Modality | Hardware Interface | Update Rate | Expected Accuracy | Primary Failure Mode | Detection & Fallback Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Down-Facing Camera** | MIPI-CSI-2 / USB 3.0 | 30–60 Hz | 0.2 px reprojection | Exposure blowout / lens occlusion | Frame drop watchdog; fallback to ESEKF dead-reckoning. |
| **6-DoF IMU** | SPI (Internal Pixhawk) | 100–200 Hz | $0.05^\circ/\text{s}$ gyro noise | Thermal bias drift, vibration saturation | Online bias estimation; vibration dampening mount. |
| **1D LiDAR Rangefinder** | UART / I2C | 50 Hz | $\pm 1.5\text{ cm}$ ($< 10\text{m}$) | Specular surface reflection / absorption | Outlier rejection gate; fallback to barometric altimeter. |
| **Barometric Altimeter** | I2C (Internal) | 20 Hz | $\pm 0.3\text{ m}$ relative | Ground-effect pressure wave surge | Reject baro spikes near ground ($< 1\text{m}$); rely on LiDAR. |
| **GNSS / RTK (Optional)**| UART (MAVLink GPS) | 5–10 Hz | $1.5\text{ m}$ (GPS) / $2\text{cm}$ (RTK)| Multi-path reflection / jamming | Covariance monitoring; complete isolation during visual approach.|

---

## 14. Sensor Fusion: Error-State Extended Kalman Filter (ESEKF)

### 14.1 Mathematical Formulation & State Vector
The core state estimator tracks the **true nominal state** $x$ and models uncertainty via a **15-dimensional error state** $\delta x$:

$$\delta x = \begin{bmatrix} \delta p \\ \delta v \\ \delta \theta \\ \delta a_b \\ \delta \omega_b \end{bmatrix} \in \mathbb{R}^{15}$$

Where:
* $\delta p \in \mathbb{R}^3$: Position error vector in World Frame ($x, y, z$).
* $\delta v \in \mathbb{R}^3$: Linear velocity error vector ($\dot{x}, \dot{y}, \dot{z}$).
* $\delta \theta \in \mathbb{R}^3$: Small-angle attitude rotation error (Lie algebra error quaternion).
* $\delta a_b \in \mathbb{R}^3$: Accelerometer bias drift.
* $\delta \omega_b \in \mathbb{R}^3$: Gyroscope bias drift.

### 14.2 Prediction & Measurement Update Cycle
1. **Continuous High-Rate IMU Propagation (100 Hz)**:
   $$\dot{p} = v, \quad \dot{v} = R(q)(a_m - a_b) + g, \quad \dot{q} = \frac{1}{2} q \otimes (\omega_m - \omega_b)$$
2. **Discrete Vision & Rangefinder Correction (30 Hz / 50 Hz)**:
   $$K_k = P_{k|k-1} H_k^T (H_k P_{k|k-1} H_k^T + R_k)^{-1}$$
   $$\delta x_k = K_k (z_k - h(\hat{x}_{k|k-1}))$$
   $$P_{k|k} = (I - K_k H_k) P_{k|k-1}$$
3. **Error Injection & Reset**: Error state $\delta x$ is injected back into nominal quaternion and position, then reset to zero.

---

## 15. Landing Intelligence State Machine (FSM)

```
                                  +-------------------+
                                  |    1. SEARCHING   |
                                  +---------+---------+
                                            | Target detected (5 frames)
                                            v
                                  +-------------------+
                                  |    2. ACQUIRED    |
                                  +---------+---------+
                                            | Verified Pad Signature
                                            v
                                  +-------------------+
                                  |    3. TRACKING    |
                                  +---------+---------+
                                            | PnP Pose Solved (Level 2/1)
                                            v
                                  +-------------------+
                                  |  4. PAD_DETECTED  |
                                  +---------+---------+
                                            | Lateral Offset > 0.15m
                                            v
                                  +-------------------+
                                  |    5. ALIGNING    |
                                  +---------+---------+
                                            | Offset < 0.15m & Attitude < 5 deg
                                            v
                                  +-------------------+
                                  |   6. APPROACHING  |
                                  +---------+---------+
                                            | Altitude < 0.8m & Velocity stable
                                            v
                                  +-------------------+
                                  | 7. LANDING_READY  |
                                  +---------+---------+
                                            | Invariant Checks 100% Green
                                            v
                                  +-------------------+
                                  |    8. LANDING     |
                                  +---------+---------+
                                            | Touchdown / Weight-on-wheels
                                            v
                                  +-------------------+
                                  |     9. LANDED     | (Motors Disarmed)
                                  +-------------------+

+-----------------------------------------------------------------------------------------+
|                                 SAFETY OVERRIDE STATES                                  |
|                                                                                         |
|  +--------------------+   (Temporary sensor glitch)     +----------------------------+  |
|  |     10. HOLD       | <-----------------------------> | Active Operational State   |  |
|  +---------+----------+                                 +----------------------------+  |
|            | Timeout > 3.0s or Invariant Breach                                         |
|            v                                                                            |
|  +--------------------+                                 +----------------------------+  |
|  |     11. ABORT      | ------------------------------> | 12. RECOVERY (Climb to 15m)|  |
|  +--------------------+                                 +----------------------------+  |
+-----------------------------------------------------------------------------------------+
```

---

## 16. Deterministic Safety Architecture

```
+------------------------------------+
|  PROBABILISTIC AI VISION PIPELINE  |
+-----------------+------------------+
                  | Proposes Trajectory Setpoint (x_des, v_des, yaw_des)
                  v
       +-----------------------------------------------+
       |       DETERMINISTIC SAFETY SUPERVISOR         |
       | - Invariant 1: Positional Covariance Limit    |
       | - Invariant 2: Descent Velocity Envelope      |
       | - Invariant 3: Maximum Tilt Envelope (<20 deg)|
       | - Invariant 4: Optical Flow Health Check      |
       | - Invariant 5: Vision Timeout Watchdog (<1.0s)|
       | - Invariant 6: Altitude Sensor Mismatch Gate  |
       +-----------------------+-----------------------+
                               |
              +----------------+----------------+
              |                                 |
     [ ALL INVARIANTS PASS ]           [ INVARIANT BREACH ]
              |                                 |
              v                                 v
+-------------------------------+   +------------------------------------+
| Dispatch Validated MAVLink    |   | IMMEDIATE DETERMINISTIC FAIL-SAFE: |
| Setpoint to Flight Controller |   | 1. HOLD (Zero Vel Hover)           |
+-------------------------------+   | 2. CLIMB ABORT (1.5 m/s climb)     |
                                    | 3. AUTOPILOT RTL (Hard Serial Cut) |
                                    +------------------------------------+
```

---

## 17. Simulation Strategy & Canonical Scenarios

The test harness executes **18 automated simulation scenarios** on every build:
1. **SC-01**: Nominal Static Landing (Zero wind, clear daylight).
2. **SC-02**: Twilight Operation (20 lux illumination).
3. **SC-03**: Solar Specular Glare (Direct sun reflection on landing pad).
4. **SC-04**: Transient Visual Occlusion (1.0s total camera blockage).
5. **SC-05**: Prolonged Occlusion Abort (3.5s blockage triggering climb).
6. **SC-06**: Linear Moving Target ($1.5\text{ m/s}$ dynamic pad recovery).
7. **SC-07**: Maritime Oscillating Pad (Simulated $10^\circ$ ship roll/heave).
8. **SC-08**: Extreme Wind Shear (8 m/s base wind with 12 m/s lateral gusts).
9. **SC-09**: Tilt Limit Violation Abort ($15\text{ m/s}$ sustained crosswind).
10. **SC-10**: LiDAR Sensor Dropout ($2.5\text{m}$ altitude sensor failure).
11. **SC-11**: FPS Starvation Stress (Frame rate drops from 30 to 5 FPS).
12. **SC-12**: Ground Clutter & Distractor Target (False circular pad nearby).
13. **SC-13**: High-Angle Diagonal Approach ($8\text{m}$ initial lateral offset).
14. **SC-14**: MAVLink Telemetry Jitter ($500\text{ms}$ simulated link lag).
15. **SC-15**: Low-Texture Surface Approach (Featureless white floor).
16. **SC-16**: Dynamic Obstacle Abort & Re-Approach Cycle.
17. **SC-17**: Companion Computer Total Power Cut (Hardware watchdog verification).
18. **SC-18**: In-Flight Safety Pilot RC Handover Override.

---

## 18. Robotics & Flight Controller Interface

### 18.1 MAVLink 2.0 Message Protocol Architecture
* **Inbound Telemetry Stream (Autopilot $\to$ Companion)**:
  * `HEARTBEAT` (1 Hz): Mode monitoring.
  * `ATTITUDE` (50 Hz): Roll, pitch, yaw, and angular rates.
  * `LOCAL_POSITION_NED` (50 Hz): Autopilot local odometry.
  * `DISTANCE_SENSOR` (50 Hz): Rangefinder distance reading.
* **Outbound Guidance Stream (Companion $\to$ Autopilot)**:
  * `SET_POSITION_TARGET_LOCAL_NED` (30–50 Hz): Position setpoints $(\vec{p}_{sp})$, velocity feedforward $(\vec{v}_{sp})$, and yaw setpoint $(\psi_{sp})$.
  * `VISION_POSITION_ESTIMATE` (30 Hz): ESEKF visual odometry injection into PX4 `EKF2` estimator.

---

## 19. Software Architecture

```
+-----------------------------------------------------------------------------------------+
|                                    SOFTWARE STACK                                       |
+-----------------------------------------------------------------------------------------+
| FRONTEND LAYER:                                                                         |
| React 18 + Next.js + TypeScript + TailwindCSS + Three.js (3D Corridor) + Lucide Icons  |
+-----------------------------------------------------------------------------------------+
| API & GATEWAY LAYER:                                                                    |
| FastAPI (Python 3.10) + WebSockets + gRPC Gateway + Pydantic v2 Models                  |
+-----------------------------------------------------------------------------------------+
| CORE PERCEPTION & ROBOTICS (EDGE):                                                      |
| C++20 Core + OpenCV 4.8 (CUDA) + TensorRT 8.6 + MAVLink 2.0 C-Library + Eigen3         |
+-----------------------------------------------------------------------------------------+
| AI DEBRIEF & ANALYTICS:                                                                 |
| LangChain / LlamaIndex + Vector DB (ChromaDB) + Pandas / Polars DataFrames              |
+-----------------------------------------------------------------------------------------+
| STORAGE & DATABASE LAYER:                                                               |
| TimescaleDB (Time-Series Telemetry) + PostgreSQL (Metadata) + MinIO / S3 (MCAP Logs)    |
+-----------------------------------------------------------------------------------------+
```

---

## 20. Database Design

```
+-------------------+       +--------------------+       +---------------------+
|      USERS        |       |      MISSIONS      |       |       FLIGHTS       |
|-------------------|       |--------------------|       |---------------------|
| id (UUID, PK)     |<----->| id (UUID, PK)      |<----->| id (UUID, PK)       |
| username (VARCHAR)|       | user_id (UUID, FK) |       | mission_id (UUID,FK)|
| role (VARCHAR)    |       | name (VARCHAR)     |       | start_time (TIMESTP)|
| created_at (TIMEST|       | status (VARCHAR)   |       | end_time (TIMESTP)  |
+-------------------+       +--------------------+       | outcome (VARCHAR)   |
                                                         +----------+----------+
                                                                    |
                                 +----------------------------------+----------------------------------+
                                 |                                  |                                  |
                                 v                                  v                                  v
                      +----------------------+           +----------------------+           +----------------------+
                      |      TELEMETRY       |           |     SAFETY_EVENTS    |           |   LANDING_ATTEMPTS   |
                      |----------------------|           |----------------------|           |----------------------|
                      | time (TIMESTAMPTZ,PK)|           | id (UUID, PK)        |           | id (UUID, PK)        |
                      | flight_id (UUID, FK) |           | flight_id (UUID, FK) |           | flight_id (UUID, FK) |
                      | pos_x, pos_y, pos_z  |           | timestamp (TIMESTMP) |           | final_error_x, y, z  |
                      | vel_x, vel_y, vel_z  |           | event_type (VARCHAR) |           | duration_sec (FLOAT) |
                      | roll, pitch, yaw     |           | severity (VARCHAR)   |           | status (SUCCESS/FAIL)|
                      | fsm_state (VARCHAR)  |           | action_taken(VARCHAR)|           | pad_type (VARCHAR)   |
                      +----------------------+           +----------------------+           +----------------------+
```

---

## 21. API Architecture

```
API Taxonomy:
├── /api/v1/auth
│   ├── POST /login
│   └── POST /refresh
├── /api/v1/missions
│   ├── GET  /
│   └── POST /create
├── /api/v1/flights
│   ├── GET  /{flight_id}
│   └── GET  /{flight_id}/telemetry/stream (WebSocket)
├── /api/v1/perception
│   ├── GET  /models
│   └── POST /models/switch
├── /api/v1/safety
│   ├── GET  /invariants
│   └── POST /override/abort
└── /api/v1/assistant
    └── POST /debrief
```

---

## 22. Real-Time Communication Protocols
* **Telemetry Streaming**: Binary WebSocket channel broadcasting Protobuf packets at 30 Hz.
* **Heartbeat & Stale Data Protocol**: Client transmits ping every 1000ms. If no server packet received for $> 500\text{ms}$, UI triggers "DATA STALE" warning and halts real-time command inputs.

---

## 23. Ground Control Dashboard (14 Planned Views)

```
GCS Screen Layouts:
1.  Mission Dashboard: Fleet overview, active airframes, mission queue.
2.  Live Mission Console: Glass-to-glass primary flight display.
3.  Camera View: Raw and augmented video streams with low-latency WebRTC.
4.  Perception Monitor: Bounding box overlays, keypoints, class confidences.
5.  Tracking Panel: Active track IDs, Kalman filter trails, covariance bounds.
6.  Landing Guidance HUD: 3D perspective corridor, glide slope, offset crosshairs.
7.  Telemetry Panel: Numerical readout of altitude, attitude, velocities.
8.  Sensors Health: Real-time status indicators for Camera, IMU, LiDAR, Baro.
9.  Safety Supervisor: Real-time invariant pass/fail matrix and override triggers.
10. Flight History: Searchable repository of completed missions.
11. Analytics Studio: Statistical plots of touchdown error, approach speed, jitter.
12. System Health: Edge compute CPU/GPU loads, thermal profiles, memory RSS.
13. AI Debrief Assistant: Interactive diagnostic chat querying flight telemetry.
14. Settings & Calibration: Camera intrinsics manager, safety threshold editor.
```

---

## 24. AI Debrief Assistant (Non-Flight-Critical)

The AI Assistant operates exclusively post-flight or during supervisory review:
* **Architecture**: Retrieval-Augmented Generation (RAG) system querying the PostgreSQL/TimescaleDB mission telemetry database and safety logs.
* **Grounding Guarantee**: Operates strictly on deterministic telemetry SQL queries; zero hallucinated flight metrics.
* **Capabilities**: Answers questions such as: *"Why was landing aborted at timestamp 14:22:05?"*, *"What was the average touchdown error across today's 10 flights?"*, *"Did sensor fusion experience covariance spikes during approach?"*.

---

## 25. Edge Computing & Low-SWaP Deployment

| Platform Target | Compute Profile | Power Budget | Inference Optimization | Thermal Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **NVIDIA Jetson Orin Nano (8GB)** | 1024-core Ampere GPU, 6-core ARM CPU | 10W–15W | TensorRT INT8 (PTQ Calibration) | Active PWM cooling heatsink; enclosure airflow ducting. |
| **Raspberry Pi 5 (8GB)** | Quad-core Cortex-A76 @ 2.4GHz | 5W–10W | ONNXRuntime ARM NEON / NCNN FP16 | Aluminum active cooler; CPU governor performance profile. |

---

## 26. Cloud Architecture & Data Lake
* **Telemetry & Log Ingestion**: MinIO / AWS S3 storage for raw `.mcap` and `.mp4` recordings.
* **Model Registry & Tracking**: MLflow tracking dataset versions, INT8 calibration profiles, and precision-recall benchmarks.
* **Cloud Independence Guarantee**: Loss of cloud connectivity has zero impact on autonomous flight execution.

---

## 27. Security & Integrity Architecture
* **Authentication**: JWT-based role-based access control (Admin, Safety Pilot, Viewer).
* **Communication Security**: TLS 1.3 encryption on all WebSockets, REST APIs, and WebRTC signaling.
* **Model & Binary Verification**: SHA-256 cryptographic checksums verified before model execution on edge node.

---

## 28. Observability & Telemetry Metrics

```
Key Performance Indicators (KPIs) Monitored in Real Time:
├── Perception Health: FPS, Inference Latency (ms), Target Confidence (%)
├── Tracking Health: Active Track Age, Jitter (RMSE px), Association Distance
├── Sensor Fusion Health: Covariance Trace (m²), Innovation Residuals
├── Safety Health: Invariant Rule Status, Heartbeat Latency (ms)
└── System Health: SoC Temperature (°C), GPU Utilization (%), Memory RSS (MB)
```

---

## 29. Testing Strategy Matrix

```
+-----------------------------------------------------------------------------------------+
|                                    TESTING HIERARCHY                                    |
+-----------------------------------------------------------------------------------------+
| 1. Unit Tests (GoogleTest / PyTest): Math, PnP, Coordinate Transforms (100% Code Cov)   |
+-----------------------------------------------------------------------------------------+
| 2. CV Regression Tests: Benchmarking against 1,000 Hard Adversarial Frames (mAP >= 92%) |
+-----------------------------------------------------------------------------------------+
| 3. Simulation Tests (Gazebo + PX4 SITL): Automated execution of 18 Canonical Scenarios   |
+-----------------------------------------------------------------------------------------+
| 4. Hardware-in-the-Loop (HIL): Jetson + Pixhawk connected over physical serial UART     |
+-----------------------------------------------------------------------------------------+
| 5. Fault Injection Tests: Simulated sensor dropouts, frame drops, serial disconnections |
+-----------------------------------------------------------------------------------------+
| 6. Tethered Outdoor Physical Flight: Flight cage validation with safety pilot override  |
+-----------------------------------------------------------------------------------------+
```

---

## 30. Performance Targets

| Metric Description | Initial Phase Target (V1–V9) | Final Production Target (V18) |
| :--- | :--- | :--- |
| **Edge Pipeline FPS** | $\ge 20\text{ FPS}$ (Host Sim) | $\ge 30\text{ FPS}$ (Jetson Orin Nano) |
| **End-to-End Latency**| $\le 75\text{ ms}$ | $\le 45\text{ ms}$ |
| **Detection Precision / Recall (mAP@50)** | $\ge 85.0\%$ | $\ge 95.0\%$ |
| **Static Touchdown Accuracy** | $\le 15.0\text{ cm}$ | $\le 5.0\text{ cm}$ |
| **Moving Pad Touchdown Accuracy ($1.5\text{ m/s}$)** | $\le 30.0\text{ cm}$ | $\le 10.0\text{ cm}$ |
| **Safety Invariant Response Time** | $\le 50\text{ ms}$ | $\le 20\text{ ms}$ |
| **Maximum Recoverable Crosswind** | $4.0\text{ m/s}$ | $8.0\text{ m/s}$ (with gusts to $12\text{ m/s}$) |

---

## 31. Development Volumes Roadmap (V0 through V18)

```
+-----------------------------------------------------------------------------------------+
|                                DEVELOPMENT VOLUMES (V0 - V18)                           |
+-----------------------------------------------------------------------------------------+
| PHASE 1: FOUNDATION & PERCEPTION                                                        |
| * V0: Repository & Baseline Audit (Catalog existing code, clean licenses, set structure)|
| * V1: Architecture Foundation & Build System (CMake, Docker, C++20, Python environments)|
| * V2: Perception Pipeline (YOLOv8, AprilTag, Level 2 contour, CLAHE preprocessing)     |
| * V3: Target Tracking Engine (Hungarian association, Kalman filter, One Euro smoothing)|
| * V4: Landing Pad Staged Architecture (Level 1, 2, 3 switching logic & PnP pose solver) |
+-----------------------------------------------------------------------------------------+
| PHASE 2: ESTIMATION, SAFETY & ROBOTICS                                                  |
| * V5: Coordinate Frames & Spatial Localization (Camera, Body, World, Pad frames)        |
| * V6: Multi-Sensor Fusion (15-State Error-State EKF with IMU, LiDAR, and Vision)        |
| * V7: Landing Intelligence Engine (12-State FSM, Glide-Slope, Trajectory Generator)     |
| * V8: Deterministic Safety Supervisor (12 Invariants, Watchdogs, Fail-Safe Handlers)    |
| * V9: Simulation & Synthetic Test Harness (Gazebo Harmonic, AirSim, 18 Scenarios)       |
| * V10: Robotics & MAVLink Interface (PX4 / ArduPilot MAVLink 2.0 Offboard integration)  |
+-----------------------------------------------------------------------------------------+
| PHASE 3: TELEMETRY, GCS & EDGE DEPLOYMENT                                               |
| * V11: High-Rate Telemetry & Logging (Protobuf, WebSockets, MCAP Flight Logger)         |
| * V12: Ground Control Station Dashboard (React 18, Next.js, Three.js 3D Corridor HUD)   |
| * V13: Post-Flight AI Assistant (LangChain, ChromaDB, Automated Flight Debriefing)       |
| * V14: Edge AI Optimization (TensorRT INT8 Quantization, Jetson Deployment)             |
| * V15: Model Evaluation & CI/CD Regression Pipeline (Automated Benchmark Scorecards)    |
+-----------------------------------------------------------------------------------------+
| PHASE 4: VALIDATION & PHYSICAL PROTOTYPING                                              |
| * V16: Hardware-in-the-Loop (HIL) Integration (Jetson + Pixhawk Serial Bench Test)      |
| * V17: Tethered & Flight Cage Physical Prototyping (Airframe integration, RC overrides) |
| * V18: Final Demonstration & Verification (Complete autonomous mission on moving pad)   |
+-----------------------------------------------------------------------------------------+
```

---

## 32. Hardware Roadmap (Level A, B, C)

```
Level A: Simulation & Software-Only (Zero HW Purchase)
├── Host PC: Intel i7 / Ryzen 7, RTX 3060+, Ubuntu 22.04 LTS
├── Simulator: Gazebo Harmonic + PX4 SITL + Web GCS
└── Gating: Must pass all 18 simulation scenarios before advancing.

Level B: Low-Cost Bench Prototype (~$600 - $900)
├── Compute: Raspberry Pi 5 (8GB) or NVIDIA Jetson Nano 4GB
├── Autopilot: Pixhawk 6C / Pixhawk 4 with PX4 Autopilot
├── Sensors: Pi Camera Module 3 + Benewake TFmini-S LiDAR
└── Gating: Complete benchtop HIL validation without propellers.

Level C: Production Edge Airframe (~$2,500 - $4,500)
├── Compute: NVIDIA Jetson Orin Nano (8GB) / Orin NX (16GB)
├── Autopilot: Cube Orange+ (Triple Redundant IMU)
├── Sensors: Sony IMX296 Global Shutter CSI + Lightware SF11/C LiDAR
└── Gating: Tethered cage testing under strict safety pilot supervision.
```

---

## 33. Dataset Strategy & Curation

* **Volume Targets**: 25,000 synthetic frames (domain randomized) + 5,000 real flight frames.
* **Splits**: 70% Train, 15% Validation, 15% Test.
* **Adversarial Benchmark**: 1,000 frozen edge-case frames used to gate model release in CI/CD.

---

## 34. Risk Register Summary

*(Refer to [docs/planning/risk-register.md](file:///c:/Users/Devendraprasad/Downloads/Drone-Landing-Perception-System-main/Drone-Landing-Perception-System-main/docs/planning/risk-register.md) for full RPN details).*
* **RSK-01 (False Positive Detection)** $\to$ Solved via Multi-Stage Level 1/2 Verification.
* **RSK-02 (Motion Blur Loss)** $\to$ Solved via High-Shutter Camera + ESEKF Dead-Reckoning.
* **RSK-03 (Altimeter Scale Ambiguity)** $\to$ Solved via Mandatory Hardware 1D LiDAR.
* **RSK-04 (Thermal Throttling)** $\to$ Solved via TensorRT INT8 Quantization + Active PWM Cooling.
* **RSK-05 (MAVLink Disconnect)** $\to$ Solved via Pixhawk Hardware Heartbeat Watchdog RTL.

---

## 35. Ethics & Responsible Engineering

* **Human-in-the-Loop Supremacy**: Autonomous control can be instantly overridden by the human safety pilot at any microsecond via hardware RC switch.
* **No Unsubstantiated Claims**: Simulation achievements are never represented as physical flight certifications.
* **Safety Isolation**: Probabilistic AI is strictly isolated from flight-critical emergency abort pathways.

---

## 36. Final Demonstration Sequence

```
1. Autonomous Mission Start: Drone arrives at terminal waypoint (30m altitude).
2. Global Acquisition: Level 3 YOLO detector locks landing zone in camera FOV.
3. Descent Initiation: ESEKF fuses visual bearing, IMU, and LiDAR altimeter.
4. Pad Transition: Pipeline transitions to Level 2 contour & Level 1 AprilTag lock.
5. Moving Target Synchronization: ESEKF tracks pad velocity (1.5 m/s); drone matches speed.
6. Alignment Confirmation: Lateral offset < 5cm, attitude aligned within 3 degrees.
7. Terminal Touchdown: Smooth exponential touchdown, motor disarm confirmed.
8. Post-Mission Analytics: Complete MCAP log persisted; AI Assistant generates debrief report.
```

---

## 37. MNC-Level System Engineering Standards

This project plan demonstrates world-class engineering across twelve core disciplines:
1. **AI/ML Engineering**: Quantized TensorRT edge inference, active learning pipelines, MLOps.
2. **Computer Vision**: PnP pose geometry, camera calibration, optical flow, fiducial tracking.
3. **Robotics & State Estimation**: Error-State EKF, quaternion kinematics, MAVLink integration.
4. **Safety Engineering**: Formally bounded invariants, dual-channel fail-safe isolation.
5. **Real-Time Systems**: Preempt-RT Linux, zero-allocation C++20, sub-45ms latency budgets.
6. **Simulation & Verification**: Hardware-in-the-Loop, Gazebo Harmonic, automated scenario suites.
7. **Distributed Systems & Backend**: Fast WebSockets, gRPC, TimescaleDB, MinIO S3 lakes.
8. **Modern Frontend Engineering**: React 18, Three.js 3D visualization, WebRTC low-latency video.
9. **Security & Cryptography**: TLS 1.3, SHA-256 model signing, JWT RBAC authentication.
10. **Observability & DevOps**: Structured logging, Prometheus metrics, Docker containerization.
11. **Software Craftsmanship**: Clean architecture, strict modularity, comprehensive test coverage.
12. **Systems Architecture**: Cohesive edge-to-cloud design with zero single points of failure.

---

## 38. Final Project Deliverables Catalog

```
Deliverables Summary:
├── 1. Complete Source Code: Edge C++20 perception core, Python services, Next.js GCS.
├── 2. AI Models: Quantized TensorRT INT8 engines, fine-tuned YOLOv8 weights, calibration sets.
├── 3. Simulation Suites: Gazebo Harmonic world plugins, PX4 SITL bridges, 18 test scripts.
├── 4. Hardware-in-the-Loop Setup: UART MAVLink bridge configs, Jetson/Pixhawk deployment docs.
├── 5. Ground Control Station: Full web application with 3D HUD, WebRTC streaming, and control panels.
├── 6. Post-Flight AI Assistant: Fully indexed RAG assistant for automated mission debriefings.
├── 7. Test Harnesses: Unit tests, integration tests, CV benchmark runner, regression test suites.
├── 8. Documentation Suite: Architectural diagrams, mathematical proofs, API specs, user guides.
└── 9. Master Project Plan: Single Source of Truth governance document (PROJECT_MASTER_PLAN.md).
```
