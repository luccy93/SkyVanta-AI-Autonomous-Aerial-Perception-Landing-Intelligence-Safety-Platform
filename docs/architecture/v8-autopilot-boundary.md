# SkyVanta AI — Volume 8 Autopilot Boundary & Safety Isolation

---

## 1. Clear Division of Responsibility

SkyVanta AI enforces a strict boundary between perception/decision intelligence and flight control execution:

```
+-------------------------------------------------------------+
|              SKYVANTA AI INTELLIGENCE STACK                 |
|  • Computer Vision & Deep Perception (V1-V4)                |
|  • Spatial Frame Transformations (V5)                       |
|  • 15-State Error-State EKF Sensor Fusion (V6)              |
|  • Landing Intelligence & Safety Supervisor (V7)            |
|  • High-Level Flight Command Validation & Translation (V8)  |
+------------------------------┬------------------------------+
                               │ Strongly-Typed FlightCommand Contracts
                               │ (HOLD, ALIGN, DESCEND, ABORT)
═══════════════════════════════╪═══════════════════════════════
                    SAFETY ISOLATION BOUNDARY
═══════════════════════════════╪═══════════════════════════════
                               ▼
+-------------------------------------------------------------+
|            EXTERNAL / SIMULATED AUTOPILOT LAYER             |
|  • MockAutopilot Simulator (V8 SIL Software-in-the-Loop)    |
|  • Future MAVLink / PX4 Autopilot Bridge (V9+)              |
|  • Flight Controller / Guidance Law                         |
|  • Motor Mixing, PWM Generation, ESC Actuation              |
+-------------------------------------------------------------+
```

---

## 2. Safety Invariants Enforced at the Boundary

1. **No Motor / Actuator Control in SkyVanta**:
   SkyVanta does not generate PWM pulses, ESC commands, or low-level motor signals. All physical control is delegated to the autopilot.
2. **Simulation-Only Default**:
   `mode: simulation` is the immutable system default. Automatic scanning of serial ports, USB devices, UDP/TCP endpoints, or hardware flight controllers is prohibited.
3. **Multi-Layer External Lockout**:
   Connecting to external hardware requires `mode: external` AND `safety.allow_external: true`. Any mismatch halts startup immediately.
4. **Heartbeat Liveness & Failsafe**:
   A lost heartbeat ($> 2.5\text{ s}$) transitions the system to `FAILSAFE_DISCONNECT` and terminates command transmission.
