# SkyVanta AI — Volume 7 Architecture Specification
**Landing Intelligence State Machine & Safety Supervisor**

---

## 1. Executive Summary

Volume 7 (V7) establishes the autonomous decision and safety supervision layer for SkyVanta AI. It answers the fundamental operational question:

> **"Given the current fused state estimate, target perception, and statistical uncertainties, is it safe to progress into the next landing phase, or must the system hold, align, abort, or fault?"**

### Core Capabilities Delivered in Volume 7:
1. **Separation of Decision from Control**: V7 produces explainable **decisions only** (e.g. `CONTINUE_DESCENT`, `ALIGN`, `ABORT`). It strictly forbids direct flight/motor actuation or flight commands.
2. **11-Phase Operational State Machine**: Formal states (`IDLE`, `SEARCHING`, `TARGET_ACQUIRED`, `ALIGNING`, `APPROACHING`, `DESCENDING`, `FINAL_APPROACH`, `LANDING_CONFIRMED`, `ABORTING`, `RECOVERY`, `FAULT`).
3. **Multi-Subsystem Safety Supervisor**: Independent invariant evaluation covering estimator health, target validity, data freshness, 3-sigma statistical uncertainties, velocity limits, and alignment envelopes.
4. **Hierarchical Abort Prioritization**: Deterministic safety priority ordering (`CRITICAL_FAULT` > `ESTIMATOR_UNHEALTHY` > `TARGET_LOST` > `UNCERTAINTY_HIGH` > `VELOCITY_HIGH` > `ALIGNMENT_FAILURE`) ensuring abort conditions always dominate normal progression.
5. **Multi-Frame Landing Persistence**: Landing confirmation requires persistent satisfaction of touchdown criteria across a configurable consecutive frame window ($N \ge 10$), preventing spurious single-frame confirmations.
6. **Latched Fault Behavior**: Critical hardware and software faults immediately trigger the terminal `FAULT` state, requiring an explicit reset.
7. **Explainable Structured Decisions**: Every emitted `LandingDecision` includes unique decision codes, primary reason codes, contributing reason codes, uncertainty metrics, and execution telemetry.

---

## 2. Decision Flow Architecture

```
V4: Landing Pad Pose (T_cam_pad)
             ↓
V5: Body/World Spatial Frame Transform (T_body_pad)
             ↓
V6: Fused State Estimate & 3σ Covariance (ESEKF)
             ↓
+-------------------------------------------------------------+
|               V7 LANDING SAFETY SUPERVISOR                  |
|  • Invariant 1: Estimator Health & Freshness                |
|  • Invariant 2: Target Validity & Reprojection Error        |
|  • Invariant 3: 3-Sigma Position/Velocity/Attitude Bounds   |
|  • Invariant 4: Horizontal & Vertical Speed Envelopes       |
|  • Invariant 5: Geometric Alignment Envelope                |
|  • Invariant 6: Multi-Frame Touchdown Persistence           |
+------------------------------┬------------------------------+
                               │
               ┌───────────────┴───────────────┐
               │                               │
        [ Safety Breach ]              [ All Invariants Pass ]
               │                               │
               ▼                               ▼
    [ Abort / Recovery / Fault ]   [ Safe State Machine Progression ]
               │                               │
               └───────────────┬───────────────┘
                               │
                               ▼
        [ Explainable LandingDecision + Telemetry Event ]
```

---

## 3. Performance Benchmarks

* **Supervisory Decision Step Latency**: **16.41 µs** (~60,900 Hz throughput)
* **Single-Core CPU Utilization at 30 Hz**: $< 0.1\%$
