# SkyVanta AI — System Scope & Boundaries

## 1. Scope Definition Framework
To ensure disciplined engineering execution, prevent scope creep, and maintain safety-first rigor, the system boundaries for **SkyVanta AI** are strictly delineated into what is **IN SCOPE** for engineering development, and what is explicitly **OUT OF SCOPE** during all initial, intermediate, and pre-certification phases.

---

## 2. In-Scope Engineering Deliverables

### A. Edge Perception & Vision Processing
* Real-time target and landing-pad detection pipelines (YOLOv8/v11 Nano, ArUco/AprilTag fiducial pose estimation, Classical OpenCV contour and geometric ellipse fitting).
* Temporal multi-target tracking using Extended/Unscented Kalman Filters, One Euro smoothing filters, and Hungarian association algorithms.
* Motion estimation, dense/sparse Lucas-Kanade optical flow, perspective correction, and camera intrinsic/extrinsic calibration utilities.
* 3D perspective corridor projection and HUD telemetry overlay generation.

### B. State Estimation & Sensor Fusion
* Sensor abstraction layer interfacing with monocular/stereo cameras, 6-DoF IMU, Barometric pressure altimeters, LiDAR/sonar rangefinders, and GNSS/RTK receivers.
* Multi-sensor fusion engine (Error-State Extended Kalman Filter - ESEKF) estimating relative 3D position $(x, y, z)$, linear velocity $(\dot{x}, \dot{y}, \dot{z})$, attitude angles $(\phi, \theta, \psi)$, and associated covariance metrics.
* Dynamic estimation of landing pad velocity for moving platform recovery.

### C. Landing Intelligence & Deterministic Safety Supervisor
* Discrete finite state machine (FSM) governing operational phases: `SEARCHING`, `ACQUIRED`, `TRACKING`, `PAD_DETECTED`, `ALIGNING`, `APPROACHING`, `LANDING_READY`, `LANDING`, `LANDED`, `HOLD`, `ABORT`, `RECOVERY`.
* Rule-based, non-neural safety supervisor implementing watchdog timers, boundary envelope checks (descent velocity limit, crosswind lateral drift limit, tilt limit, covariance thresholding, optical flow health).
* Fail-safe execution layer generating override signals (`HOLD_POSITION`, `CLIMB_ABORT`, `RETURN_TO_HOME`, `EMERGENCY_DISARM_REQUEST`).

### D. Robotics & Flight Controller Interface
* Bidirectional MAVLink communication layer (`MAVLink 2.0` over Serial/UDP) interfacing with PX4 Autopilot and ArduPilot ecosystems.
* Ingestion of high-rate telemetry (`ATTITUDE`, `LOCAL_POSITION_NED`, `HIGHRES_IMU`, `DISTANCE_SENSOR`).
* Generation of high-level guidance setpoints (`SET_POSITION_TARGET_LOCAL_NED`, `VISION_POSITION_ESTIMATE`, `LANDING_TARGET`).

### E. Simulation & Verification Pipeline
* Software-in-the-loop (SITL) and Hardware-in-the-loop (HIL) environments using Gazebo Harmonic / PX4 SITL / AirSim.
* Synthetic scenario generator supporting 15+ automated edge-case test suites (sensor dropout, visual occlusion, moving pads, extreme crosswinds, lighting variations).
* Automated regression test harness measuring tracking accuracy, latency, and false positive abort rates.

### F. Ground Control & Post-Flight Intelligence
* Real-time WebSocket/gRPC telemetry streaming to a modern web-based Ground Control Station (GCS).
* GCS user interface providing HUD visualization, trajectory analytics, safety monitor panels, and manual abort overrides.
* Non-flight-critical AI Assistant leveraging historical flight logs, sensor metrics, and telemetry databases to conduct automated mission debriefings and fault diagnostics.

---

## 3. Out-of-Scope (Initial & Intermediate Phases)

### A. Certified Aviation & Commercial Safety
* DO-178C (Software Considerations in Airborne Systems) or DO-254 (Complex Electronic Hardware) formal certification.
* Direct commercial passenger/cargo beyond-visual-line-of-sight (BVLOS) operations in unsegregated national airspace.
* Unsupervised physical flight testing without an active manual safety pilot with hardware RC override.

### B. Low-Level Flight Control Inner Loops
* Writing custom inner-loop PID attitude/motor mixers from scratch (relies entirely on established open-source flight stacks like PX4/ArduPilot for low-level motor dynamics).
* Direct PWM/DShot motor ESC signaling from the edge AI companion computer.

### C. Latency-Critical Cloud Dependencies
* Any cloud-based remote inference or control loops for active flight guidance (all real-time perception, state estimation, and safety decisions must execute 100% on-edge).
* Real-time video streaming over cellular/satellite as a requirement for autonomous landing execution.

### D. Unrestricted Physical Autonomy
* Autonomous flight in public spaces, dense urban environments, or adverse storm conditions prior to thorough SITL/HIL validation and institutional safety approval.
