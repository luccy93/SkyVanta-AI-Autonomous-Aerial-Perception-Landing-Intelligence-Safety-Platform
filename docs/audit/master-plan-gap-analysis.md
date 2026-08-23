# SkyVanta AI — Master Plan Gap Analysis (V0)

## 1. Comprehensive Capability Reconciliation Table

```
+-----------------------------------------------------------------------------------------------------------------------+
|                                          MASTER PLAN VS. CURRENT REPOSITORY RECONCILIATION                            |
+-----------------------------------------------------------------------------------------------------------------------+
```

| Capability / Subsystem | Master Plan Specification | Current Repository Implementation | Implementation Status | Technical Gap to Close | Development Priority |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **YOLO Target Detector** | YOLOv8-Nano / v11-Nano fine-tuned on drone airframes & landing pads (TensorRT INT8) | Pretrained `yolov8n.pt` filtering standard COCO proxy classes (`bird`, `airplane`, etc.) | **PROTOTYPE** | Needs custom dataset training, fine-tuning on pads, and INT8 TensorRT export. | **HIGH (V2)** |
| **Fiducial Tag Detector** | Multi-resolution nested AprilTag 3 (tag36h11) & ArUco (DICT_6X6) for sub-cm touchdown | *Completely absent.* | **NOT IMPLEMENTED** | Integrate `pupil-apriltags` / OpenCV ArUco detector with camera calibration. | **CRITICAL (V4)** |
| **Target Tracking** | Multi-target Hungarian association + 3D metric Kalman filter | Single-target greedy IoU + 2D pixel-space `KalmanBox2D` | **PARTIAL** | Upgrade to Hungarian matcher, multi-track lifecycle manager, and 3D metric state. | **HIGH (V3)** |
| **Smoothing Filters** | One Euro Filter on 3D pose and trajectory setpoints | `OneEuroFilter` & `Vec2EuroFilter` on 2D pixel coordinates | **IMPLEMENTED** | Reusable as-is; wrap in clean module and apply to 3D states. | **LOW (V3)** |
| **PnP Pose Estimation** | SolvePnP (SOLVEPNP_IPPE) deriving 6-DoF relative transformation $T_{pad}^{cam}$ | *Completely absent.* | **NOT IMPLEMENTED** | Implement camera calibration matrix $K$ and PnP planar solver for pads. | **CRITICAL (V4, V5)** |
| **Sensor Abstraction** | Unified interfaces for Camera, 6-DoF IMU, 1D LiDAR rangefinder, Barometer, GNSS | *Completely absent.* (Reads offline video files only). | **NOT IMPLEMENTED** | Build sensor interface classes with timestamp synchronization and noise models. | **HIGH (V6)** |
| **Sensor Fusion (ESEKF)** | 15-State Error-State EKF fusing Camera PnP, IMU, LiDAR, and dynamic pad velocity | *Completely absent.* | **NOT IMPLEMENTED** | Implement 15-state quaternion-based Error-State EKF in C++ and Python. | **CRITICAL (V6)** |
| **Landing State Machine** | 12-State FSM (`SEARCHING` to `LANDED`, plus `HOLD`, `ABORT`, `RECOVERY`) | 5-State confidence-driven heuristic FSM (`SEARCHING` to `APPROACHING`) | **PROTOTYPE** | Redesign FSM to incorporate physical descent gates, hold/abort states, and safety triggers. | **HIGH (V7)** |
| **Safety Supervisor** | Independent deterministic supervisor evaluating 12 hard invariant rules at 50 Hz | Data clamping (`clamp()`) and basic confidence thresholds | **PROTOTYPE** | Build standalone C++ safety validator with watchdog timers and fail-safe handlers. | **CRITICAL (V8)** |
| **Simulation Harness** | Gazebo Harmonic + PX4 SITL + 18 automated regression scenarios | Procedural 2D background generator (`run_demo()`) | **PROTOTYPE** | Build Gazebo camera/sensor plugins and automated scenario test harness. | **HIGH (V9)** |
| **MAVLink Interface** | MAVLink 2.0 serial protocol sending `SET_POSITION_TARGET_LOCAL_NED` to PX4/ArduPilot | *Completely absent.* | **NOT IMPLEMENTED** | Implement asynchronous MAVLink communication layer with heartbeat watchdog. | **HIGH (V10)** |
| **Telemetry & Logging** | Protobuf / WebSocket telemetry streaming (30 Hz) + MCAP lossless flight logging | Real-time console printouts and offline MP4 video overlay | **PROTOTYPE** | Implement WebSocket gateway and MCAP time-series flight logger. | **MEDIUM (V11)** |
| **Ground Control Station**| Next.js + React 18 + Three.js 3D perspective corridor + WebRTC live video stream | OpenCV window / rendered MP4 video file | **PROTOTYPE** | Build modern browser-based GCS frontend with interactive override controls. | **MEDIUM (V12)** |
| **AI Debrief Assistant** | RAG-based LLM assistant querying PostgreSQL/TimescaleDB flight telemetry & safety logs | *Completely absent.* | **NOT IMPLEMENTED** | Build post-flight telemetry vector store and diagnostic query interface. | **LOW / LATE (V13)** |
| **Edge Optimization** | TensorRT INT8 quantization on NVIDIA Jetson Orin Nano ($< 15\text{W}$ consumption) | Standard PyTorch / OpenCV on host CPU/GPU | **NOT IMPLEMENTED** | Build ONNX export and TensorRT INT8 calibration pipeline. | **MEDIUM (V14)** |
| **Automated Testing & CI**| GoogleTest + PyTest + CI/CD regression benchmark across 1,000 hard frames | *Zero test suites on disk.* | **NOT IMPLEMENTED** | Set up GitHub Actions CI/CD with automated unit, integration, and CV test runners. | **HIGH (V1)** |
