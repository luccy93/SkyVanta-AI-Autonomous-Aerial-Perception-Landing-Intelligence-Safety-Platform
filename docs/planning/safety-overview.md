# SkyVanta AI — Safety Architecture & Fail-Safe Specification

## 1. Core Safety Philosophy
In autonomous aerial robotics, **safety is an independent architectural layer, never an output of a probabilistic model**. Deep learning models are inherently stochastic; their outputs cannot be guaranteed under out-of-distribution conditions (lens flare, camera distortion, extreme weather, unfamiliar landing surface textures).

SkyVanta AI enforces a **Dual-Channel Architecture**:
1. **The Intelligence Channel (Probabilistic)**: AI vision, neural detection, optical flow, and trajectory generation propose optimal landing trajectories.
2. **The Safety Channel (Deterministic)**: A rule-based, formally verifiable safety supervisor continuously computes validation envelopes. It possesses absolute veto power over the intelligence channel.

```
+------------------------------------+
|  AI Vision & Landing Intelligence  |
+-----------------+------------------+
                  | Proposes Trajectory / Setpoint
                  v
       +--------------------+
       |  SAFETY SUPERVISOR | <--- Hard Invariant Rules & Watchdogs
       +----------+---------+
                  |
        +---------+---------+
        |                   |
[ Invariant PASSED ]   [ Invariant VIOLATED ]
        |                   |
        v                   v
+---------------+   +------------------------------------+
| Send Setpoint |   | Trigger Deterministic Fail-Safe:   |
| to Autopilot  |   | 1. HOLD (Zero Velocity Hover)      |
+---------------+   | 2. CLIMB ABORT (Climb to Safe Alt) |
                    | 3. RTL (Return to Launch)          |
                    | 4. EMERGENCY HANDOVER (Manual RC)  |
                    +------------------------------------+
```

---

## 2. Comprehensive Safety Invariants

| Category | Invariant Rule | Operational Threshold | Trigger Condition | Fail-Safe Response |
| :--- | :--- | :--- | :--- | :--- |
| **Vision Loss** | `INV_VISION_TIMEOUT` | $\Delta t_{vision} > 1.0\text{ s}$ during approach | Frame drop / target occlusion | `HOLD` hover; if $> 3.0\text{ s}$, `ABORT` climb |
| **Drift Velocity** | `INV_LATERAL_VEL` | $\|v_{xy}\| > 1.5\text{ m/s}$ (below 3m altitude) | Wind gust or erratic trajectory | `HOLD` position, damp horizontal velocity |
| **Descent Velocity**| `INV_VERTICAL_VEL` | $v_z > 0.8\text{ m/s}$ ($z > 2\text{m}$), $v_z > 0.3\text{ m/s}$ ($z \le 0.5\text{m}$) | Over-aggressive descent | Cap descent rate to maximum safe envelope |
| **Attitude Limits**| `INV_TILT_LIMIT` | $\|\phi\| > 20^\circ$ or $\|\theta\| > 20^\circ$ | High turbulence or oscillation | Level aircraft, abort visual landing |
| **State Covariance**| `INV_COV_BOUND` | $\text{Trace}(P_{pos}) > 0.35\text{ m}^2$ | Sensor divergence / Kalman filter blowup | Freeze landing state, transition to `HOLD` |
| **Range Discrepancy**| `INV_ALT_MISMATCH`| $\|z_{vision} - z_{lidar}\| > 0.4\text{ m}$ for 300ms | Scale ambiguity or ground distortion | Discard vision $z$, use LiDAR $z$ |
| **Optical Flow Drop**| `INV_FLOW_HEALTH` | Valid track points $< 15$ | Low texture / feature starvation | Inhibit fast horizontal maneuvers |
| **Moving Pad Delta** | `INV_PAD_MAX_SPEED`| $\|v_{pad}\| > 3.0\text{ m/s}$ or acceleration $> 1.0\text{ m/s}^2$| Moving platform maneuvering violently | Inhibit touchdown, maintain relative standoff |
| **Heartbeat Loss** | `INV_HEARTBEAT` | MAVLink/IPC heartbeat $> 250\text{ ms}$ | Process crash or serial cable disconnect | Autopilot failsafe engages automatically |
| **Manual RC Override**| `INV_RC_OVERRIDE`| RC Mode Switch $\ne$ OFFBOARD / AUTO | Pilot takes control on transmitter | Instantaneous release of companion control |

---

## 3. Landing Finite State Machine (FSM) Specification

```
      +------------+
      | SEARCHING  |<--------------------------------------------------+
      +-----+------+                                                   |
            | Target Detected (N >= 5 frames)                          |
            v                                                          |
      +------------+                                                   |
      |  ACQUIRED  |                                                   |
      +-----+------+                                                   |
            | Pad Verified & Bounding Box Stable                       |
            v                                                          |
      +------------+                                                   |
      |  TRACKING  |                                                   |
      +-----+------+                                                   |
            | Level 2/1 Pad Lock & PnP Pose Valid                      |
            v                                                          |
      +---------------+                                                |
      | PAD_DETECTED  |                                                |
      +-----+---------+                                                |
            | Offset > Tolerance                                       |
            v                                                          |
      +------------+                                                   |
      |  ALIGNING  |                                                   |
      +-----+------+                                                   |
            | Alignment Error < 0.15m & Attitude < 5 deg               |
            v                                                          |
      +---------------+                                                |
      |  APPROACHING  |                                                |
      +-----+---------+                                                |
            | Altitude < 0.8m & All Safety Invariants Green            |
            v                                                          |
      +---------------+                                                |
      | LANDING_READY |                                                |
      +-----+---------+                                                |
            | Final Touchdown Sequence                                 |
            v                                                          |
      +------------+                                                   |
      |  LANDING   |                                                   |
      +-----+------+                                                   |
            | Weight-on-wheels / Disarm Detected                       |
            v                                                          |
      +------------+                                                   |
      |   LANDED   | (Mission Accomplished)                            |
      +------------+                                                   |
                                                                       |
+-------------------------------------------------------------------+  |
|                       SAFETY OVERRIDE STATES                      |  |
|                                                                   |  |
|   +----------+ (Temporary Failure / Invariant Breach)             |  |
|   |   HOLD   | ----> Resumes to TRACKING if clear within 3s       |  |
|   +----+-----+                                                    |  |
|        |                                                          |  |
|        | (Critical Violation / Timeout > 3s)                      |  |
|        v                                                          |  |
|   +----------+                                                    |  |
|   |  ABORT   | ----> Climbs to Safe Recovery Altitude (15m)       |  |
|   +----+-----+                                                    |  |
|        |                                                          |  |
|        v                                                          |  |
|   +----------+                                                    |  |
|   | RECOVERY | ---------------------------------------------------+  |
|   +----------+ (Re-initiates Search or executes RTL)                 |
+-------------------------------------------------------------------+--+
```

---

## 4. Fail-Safe Execution Protocols
1. **Protocol Alpha (HOLD / Standoff)**:
   * Target lost or transient sensor anomaly.
   * Companion computer commands zero horizontal velocity ($\vec{v}_{xy} = 0$) and holds current altitude ($z_{hold}$).
   * If valid tracking resumes within 3.0 seconds with covariance under bounds, FSM returns to `TRACKING`/`ALIGNING`.
2. **Protocol Bravo (CLIMB ABORT)**:
   * Unrecoverable loss of target, sudden obstacle intrusion, or critical descent anomaly.
   * Safety supervisor commands maximum climb rate ($1.5\text{ m/s}$) to pre-designated safety standoff altitude (e.g., $15.0\text{ m}$ AGL).
   * Transitions to `RECOVERY` to either re-acquire or hand off to Autopilot RTL.
3. **Protocol Charlie (AUTOPILOT INDEPENDENT RTL)**:
   * Companion computer hardware failure or complete OS crash.
   * PX4/ArduPilot hardware watchdog detects loss of MAVLink heartbeat from companion computer ($> 1.0\text{ s}$).
   * Flight controller automatically triggers internal fail-safe: climbs, switches to GPS navigation, and returns to home launch coordinates.
4. **Protocol Delta (MANUAL PILOT HARD OVERRIDE)**:
   * Hardware safety pilot toggles RC transmitter switch out of Offboard mode.
   * Autopilot instantly reverts to manual Stabilized/Position hold mode, completely isolating all companion computer commands.
