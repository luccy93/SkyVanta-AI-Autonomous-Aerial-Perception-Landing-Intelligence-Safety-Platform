# SkyVanta AI — Safety Capabilities Audit (V0)

## 1. Safety Mechanisms Inventory & Verification

> [!WARNING]
> While `PROJECT_MASTER_PLAN.md` specifies a comprehensive deterministic dual-channel safety supervisor with 12 hard invariant rules, this audit documents **what safety mechanisms actually exist in the current codebase**.

| Safety Feature | Verification in Current Code | Implementation Status | Level | Operational Behavior in Code |
| :--- | :--- | :---: | :---: | :--- |
| **Confidence Thresholding** | `main.py:412-421` (`_update_state`) | **IMPLEMENTED** | Level A | Tracks confidence $< 0.12 \to$ `SEARCHING`, $< 0.35 \to$ `ACQUIRED`, etc. |
| **Visual Loss Timeout** | `main.py:428, 433` (`frames_since_hit > 45`) | **PARTIALLY IMPLEMENTED** | Level A | Drops target track if not detected for 45 frames ($1.5\text{s}$). Reverts state to `SEARCHING`. |
| **Jump Distance Gate** | `main.py:390-394` | **IMPLEMENTED** | Level A | Clears trajectory trail if detected center jumps $> 4.5\%$ screen diagonal in one frame. |
| **Bounds Clamping** | `main.py:69, 384` (`clamp()` helper) | **IMPLEMENTED** | Level A | Clamps smoothed coordinates $(s_{cx}, s_{cy})$ within $[0, w]$ and $[0, h]$ image bounds. |
| **Deterministic Supervisor**| *Zero independent supervisor processes.* | **NOT IMPLEMENTED** | Level A | No dual-channel safety isolation. |
| **Invariant Rule Watchdogs**| *Zero rule watchdogs (velocity, tilt, covariance).* | **NOT IMPLEMENTED** | Level A | Invariants exist only in documentation. |
| **`HOLD` Failsafe Handler**| *No `HOLD` state in tracker FSM.* | **NOT IMPLEMENTED** | Level A | Tracker FSM only has `SEARCHING`, `ACQUIRED`, `TRACKING`, `LOCKED`, `APPROACHING`. |
| **`ABORT` Climb Handler** | *No `ABORT` state or climb command logic.* | **NOT IMPLEMENTED** | Level A | No abort setpoint generation. |
| **Sensor Loss Watchdogs** | *Zero sensor watchdogs (IMU, LiDAR, Baro).* | **NOT IMPLEMENTED** | Level A | No sensors exist in current code to monitor. |
| **Manual Pilot RC Override**| *Zero RC channel monitor or MAVLink mode checks.* | **NOT IMPLEMENTED** | Level A | System has no connection to an RC transmitter or autopilot. |
| **Heartbeat Watchdog** | *Zero heartbeat monitor.* | **NOT IMPLEMENTED** | Level A | No IPC or serial watchdog timers. |

---

## 2. Safety Assessment Summary
* **Current State**: The repository possesses basic **data-clamping and confidence-thresholding routines** appropriate for an offline video visualization pipeline.
* **Safety-Critical Readiness**: **0% ready for physical flight control**. No autonomous flight commands or physical motor activations can be safely executed until **Volume 8 (Deterministic Safety Supervisor)** is formally implemented and validated in simulation.
