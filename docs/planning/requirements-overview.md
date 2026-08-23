# SkyVanta AI — Requirements Overview

## 1. Functional Requirements (FR)

### FR-01: Visual Target & Landing Pad Detection
* **FR-01.1**: The system shall detect target landing zones using Level 1 fiducials (ArUco / AprilTag 36h11 family) from altitudes between 0.2m and 15m.
* **FR-01.2**: The system shall detect standardized geometric landing pads (circles, 'H' markers, concentric rings) using deep learning (YOLOv8/v11 Nano) and classical contour analysis from altitudes between 2m and 40m.
* **FR-01.3**: The system shall output the 2D bounding box $(u_{min}, v_{min}, u_{max}, v_{max})$, class label, detection confidence ($0.0 \le c \le 1.0$), and corner keypoints in image space.

### FR-02: Target Tracking & Smoothing
* **FR-02.1**: The system shall track the target landing zone continuously across consecutive video frames with consistent track IDs.
* **FR-02.2**: The system shall maintain track continuity across temporary visual occlusions (up to 1.5 seconds / 45 frames at 30 FPS) via Kalman state propagation.
* **FR-02.3**: The system shall apply One Euro filtering to 2D pixel coordinates and estimated 3D poses to minimize jitter without introducing latency exceeding 15ms.

### FR-03: Pose Estimation & Coordinate Transformation
* **FR-03.1**: The system shall solve Perspective-n-Point (PnP) or homography using calibrated camera intrinsic parameters $(f_x, f_y, c_x, c_y, k_1, k_2, p_1, p_2)$ to determine the 6-DoF relative transformation $T_{pad}^{camera} = [R | t]$.
* **FR-03.2**: The system shall transform relative poses into the drone Body Frame ($B$) and Local World NED Frame ($W$).

### FR-04: Multi-Sensor State Estimation & Fusion
* **FR-04.1**: The system shall ingest asynchronous data from Camera (30–60 Hz), IMU (100–200 Hz), Rangefinder (20–50 Hz), and Barometer (10–20 Hz).
* **FR-04.2**: The system shall fuse visual relative pose and inertial measurements using an Error-State EKF to estimate relative position, velocity, and landing pad dynamic state with covariance bounds.

### FR-05: Landing Intelligence & Flight FSM
* **FR-05.1**: The system shall execute a deterministic Finite State Machine (FSM) with states: `SEARCHING`, `ACQUIRED`, `TRACKING`, `PAD_DETECTED`, `ALIGNING`, `APPROACHING`, `LANDING_READY`, `LANDING`, `LANDED`, `HOLD`, `ABORT`, `RECOVERY`.
* **FR-05.2**: State transitions shall require satisfaction of temporal persistence thresholds (e.g., minimum 5 consecutive valid frames) to eliminate chatter.

### FR-06: Deterministic Safety Supervision
* **FR-06.1**: The safety supervisor shall independently monitor 12 critical flight safety indicators at $\ge 50$ Hz.
* **FR-06.2**: The safety supervisor shall immediately override AI landing guidance and issue a `HOLD` or `ABORT` command if any safety invariant is violated.

### FR-07: Telemetry & Ground Station Interface
* **FR-07.1**: The system shall stream real-time JSON/binary telemetry over WebSockets/gRPC at 20–30 Hz.
* **FR-07.2**: The system shall record full-rate MCAP/ROSbag/CSV flight logs with microsecond-level synchronization for post-flight analysis.

---

## 2. Non-Functional Requirements (NFR)

### NFR-01: Performance & Latency
* **NFR-01.1 (Edge FPS)**: Edge perception pipeline shall maintain a minimum of 30 FPS on targeted edge hardware (e.g., Jetson Orin Nano 8GB) at $1280 \times 720$ resolution.
* **NFR-01.2 (Pipeline Latency)**: Total latency from camera photon arrival to MAVLink setpoint publication shall not exceed 45 milliseconds (ms).
* **NFR-01.3 (State Fusion Rate)**: The EKF sensor fusion loop shall execute deterministically at $\ge 50$ Hz with $< 2$ ms jitter.

### NFR-02: Accuracy & Precision
* **NFR-02.1 (Terminal Touchdown Error)**: Final landing accuracy shall be within $\le 5.0$ cm of pad center in calm conditions ($\le 2$ m/s wind) and $\le 15.0$ cm in moderate wind ($\le 8$ m/s).
* **NFR-02.2 (Attitude Alignment Error)**: Heading and attitude alignment relative to the pad orientation shall be within $\pm 3.0^\circ$ at touchdown.

### NFR-03: Reliability & Robustness
* **NFR-03.1 (Lighting Invariance)**: The perception system shall maintain tracking across ambient illumination ranging from 15 lux (dusk/dawn) to 85,000 lux (direct midday sunlight).
* **NFR-03.2 (Zero Uncommanded Maneuvers)**: The system shall produce zero uncommanded hard descent maneuvers when false positive detections occur.
* **NFR-03.3 (Fault Isolation)**: AI process crashes (e.g., CUDA OOM) shall not crash the core telemetry or safety supervisor process.

### NFR-04: Security & Integrity
* **NFR-04.1**: Telemetry streams and ground station control interfaces shall support TLS 1.3 encryption and JWT-based authentication.
* **NFR-04.2**: Flight logs and model weights shall be protected with cryptographic hash verification (SHA-256).

---

## 3. Safety Integrity Requirements (SIR)

| Identifier | Safety Invariant | Threshold / Condition | Enforced Action | Response Time |
| :--- | :--- | :--- | :--- | :--- |
| **SIR-01** | Visual Target Loss | Target lost for $> 1.0$ s during `APPROACHING` / `LANDING` | Transition to `HOLD`, hover at current altitude | $\le 50$ ms |
| **SIR-02** | Covariance Explosion | Positional covariance $P_{xx,yy} > 0.25\text{ m}^2$ or $P_{zz} > 0.10\text{ m}^2$ | Freeze descent, transition to `HOLD` | $\le 20$ ms |
| **SIR-03** | Excessive Descent Rate | $v_z > 1.2\text{ m/s}$ (high altitude) or $v_z > 0.4\text{ m/s}$ (altitude $< 1.5\text{ m}$) | Throttle back descent velocity to $0.2\text{ m/s}$ | $\le 20$ ms |
| **SIR-04** | Excessive Tilt / Roll-Pitch | Tilt angle $\|\theta\| > 25^\circ$ or $\|\phi\| > 25^\circ$ | Level aircraft, transition to `ABORT` climb | $\le 20$ ms |
| **SIR-05** | Rangefinder Anomaly | Rangefinder altitude disagreeing with EKF by $> 0.5\text{ m}$ for $> 300\text{ ms}$ | Fall back to barometric altitude, reject vision height | $\le 50$ ms |
| **SIR-06** | Telemetry / MAVLink Stale | MAVLink heartbeat missing for $> 500\text{ ms}$ | Autopilot autonomous failsafe (RTL or Land) | Hardware Autopilot |
| **SIR-07** | Manual Pilot Override | RC transmitter mode switch toggled by safety pilot | Instantaneous release of companion control to manual RC | $< 5$ ms (Hardware direct) |
