# SkyVanta AI — Simulation, SITL & Verification Strategy

## 1. Multi-Stage Simulation Paradigm
Physical drone testing without rigorous virtual verification is dangerous and irresponsible. SkyVanta AI adopts a **Four-Stage Progressive Verification Pipeline**:

```
+-------------------+      +--------------------+      +--------------------+      +--------------------+
|     STAGE 1       |      |      STAGE 2       |      |      STAGE 3       |      |      STAGE 4       |
| Pure Software Sim | ---> |  PX4 / SITL Sim    | ---> |  Hardware-In-Loop  | ---> | Tethered Physical  |
| & Python Harness  |      |  (Gazebo / AirSim) |      | (Companion + Pixhawk)|    | Flight Test        |
+-------------------+      +--------------------+      +--------------------+      +--------------------+
```

---

## 2. Detailed Simulation Stages

### Stage 1: Pure Software Simulation & Replay Harness
* **Objective**: Validate computer vision algorithms, tracking filters, PnP calculations, and FSM transitions on synthetic and recorded video sequences.
* **Environment**: High-speed offline Python/C++ pipeline processing prerecorded MP4 videos, synthetic OpenCV test frames, and ground-truth camera trajectories.
* **Metrics**: IoU tracking score, bounding box jitter (RMSE), state transition correctness, processing latency per frame.

### Stage 2: Software-in-the-Loop (SITL) with Physics Simulation
* **Objective**: Validate dynamic interaction between perception, ESEKF sensor fusion, landing intelligence, and simulated PX4 aerodynamics.
* **Environment**: Gazebo Harmonic / AirSim coupled with PX4 SITL over lockstep virtual time.
* **Components**:
  * Realistic downward-facing camera plugin with noise, distortion, and exposure simulation.
  * Simulated IMU, Barometer, and Rangefinder plugins with Gaussian white noise and drift characteristics.
  * Moving landing platform model with programmatic trajectory injection.

### Stage 3: Hardware-in-the-Loop (HIL)
* **Objective**: Validate real-time performance, thermal stability, serial MAVLink communication, and CPU/GPU utilization on real physical target hardware.
* **Environment**: Physical Edge Compute (Jetson Orin Nano) connected via physical UART serial cable to physical Flight Controller (Cube Orange+ / Pixhawk 6C).
* **Components**: Gazebo SITL simulator renders camera frames streamed to the Jetson over HDMI/CSI capture or virtual RTSP; Jetson runs production vision/safety binaries and sends actual MAVLink packets back to the Pixhawk.

### Stage 4: Controlled Physical Flight Testing
* **Objective**: Real-world validation in outdoor and indoor flight cages.
* **Protocols**:
  * Geofenced flight envelope with hard boundary limits.
  * Tethered emergency line for early hover tests.
  * Dedicated safety pilot with hardware RC transmitter on high-priority override switch.

---

## 3. The 18 Canonical Simulation Test Scenarios

The automated test harness executes these 18 scenarios on every major software build to verify tracking robustness, landing accuracy, and safety fail-safe activation:

| Scenario ID | Test Scenario Name | Environmental Conditions | Injected Anomaly / Perturbation | Expected System Behavior & Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **SC-01** | Nominal Static Landing | Clear day, 1000 lux, 0 m/s wind | None (ideal baseline) | Smooth approach, landing within $\le 5$ cm of center in $< 20$ s. |
| **SC-02** | Low Light & Twilight | 15–30 lux dusk illumination | Reduced visual contrast, sensor noise | Robust level 1/2 pad detection, no false aborts. |
| **SC-03** | High Solar Glare | Direct midday sun, high reflection | Specular highlights on pad surface | CLAHE / exposure handling prevents track dropout. |
| **SC-04** | Transient Visual Occlusion | Nominal lighting | 1.0 s total obstruction of camera view | Kalman filter dead-reckoning maintains track; resumes approach. |
| **SC-05** | Prolonged Visual Occlusion | Nominal lighting | 3.5 s total obstruction of camera view | System triggers `HOLD` at 1.0s, triggers `ABORT` climb at 3.0s. |
| **SC-06** | Linear Moving Pad | Pad moving at $1.5\text{ m/s}$ ($5.4\text{ km/h}$) | Constant velocity vector | EKF tracks pad velocity; touchdown within $\le 10$ cm of pad center. |
| **SC-07** | Oscillating Maritime Pad | Pad simulating vessel roll ($10^\circ$, $0.3\text{ Hz}$) | Combined heave ($0.5\text{m}$) and pitch/roll | Approach synchronizes with wave phase; touch at heave crest. |
| **SC-08** | Severe Wind Shear & Gusts | 8 m/s base wind with 12 m/s gusts | Sudden lateral displacement ($> 1\text{m}$) | Alignment controller recovers corridor without attitude breach. |
| **SC-09** | Extreme Crosswind Abort | Sustained 14 m/s crosswind | Drone reaches maximum tilt limit ($> 20^\circ$) | Invariant `INV_TILT_LIMIT` triggers; safe `ABORT` climb. |
| **SC-10** | Rangefinder Sensor Failure | At $2.5\text{ m}$ altitude during descent | Rangefinder drops to $0.0\text{ m}$ / NaN | Invariant `INV_ALT_MISMATCH` rejects rangefinder, falls back to baro/vision. |
| **SC-11** | Camera Frame Dropout | 30 FPS drops to 5 FPS intermittently | Pipeline CPU starvation | State fusion tolerates reduced vision rate via IMU integration. |
| **SC-12** | False Positive Distractor | Ground clutter (similar circular shapes) | Distractor pad placed 2m from true pad | Level 1/2 tag ID verification rejects distractor, locks true target. |
| **SC-13** | Fast Diagonal Approach | Drone starts with $8\text{ m}$ lateral offset | Initial high visual angle | `SEARCHING` $\to$ `ACQUIRED` $\to$ `ALIGNING` corridor correction. |
| **SC-14** | MAVLink Link Degradation | 500 ms simulated telemetry latency | Jitter on MAVLink UDP connection | Safety supervisor flags stale telemetry, holds safe descent rate. |
| **SC-15** | Ground Texture Starvation | Plain featureless white landing surface | Low optical flow feature count | System relies on pad geometry and rangefinder, limits speed. |
| **SC-16** | Abort & Re-approach Cycle | Injected obstacle on pad at 1m alt | Obstacle appears, stays 5s, leaves | `ABORT` climb to 10m $\to$ `RECOVERY` $\to$ `SEARCHING` $\to$ successful landing. |
| **SC-17** | Total Companion Power Cut | Simulated companion computer freeze | Heartbeat stops completely | Pixhawk hardware failsafe triggers within 1.0s, engages native RTL. |
| **SC-18** | Manual Pilot RC Handover | Mid-descent at 2m altitude | Pilot switches RC mode switch to Manual | Instantaneous companion cutoff; pilot assumes smooth manual control. |
