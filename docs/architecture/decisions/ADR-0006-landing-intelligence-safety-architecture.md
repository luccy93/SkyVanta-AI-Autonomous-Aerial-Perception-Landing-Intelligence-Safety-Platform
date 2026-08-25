# ADR-0006: Landing Intelligence State Machine & Safety Supervisor Architecture

## Status
**ACCEPTED** (2026-08-25)

## Context
Volumes 4, 5, and 6 provide 6-DoF landing pad perception, spatial frame transformations, and a continuous 15-state ESEKF sensor fusion state estimate with covariance.
To enable autonomous landing operations, the platform requires an intelligent supervisory decision layer that decides whether it is safe to progress from target search to alignment, descent, and touchdown.

Key challenges include:
1. Strict decoupling between high-level intelligence decisions and low-level motor/flight control.
2. Defending against transient perceptual glitches without causing state oscillation.
3. Enforcing deterministic abort hierarchies when multiple faults occur simultaneously.
4. Ensuring landing touchdown cannot be triggered by a single noisy measurement frame.

## Decision

1. **Decoupled Decision Architecture**:
   - V7 emits strongly-typed `LandingDecision` contracts recommending supervisory actions (`HOLD`, `ALIGN`, `CONTINUE_DESCENT`, `ABORT`, etc.). Direct actuator, flight control, or motor commands are strictly prohibited.

2. **11-Phase State Machine Topology**:
   - A finite state machine models the full operational lifecycle (`IDLE`, `SEARCHING`, `TARGET_ACQUIRED`, `ALIGNING`, `APPROACHING`, `DESCENDING`, `FINAL_APPROACH`, `LANDING_CONFIRMED`, `ABORTING`, `RECOVERY`, `FAULT`).
   - Disallowed state transitions (e.g. `SEARCHING` $\to$ `LANDING_CONFIRMED`) raise `InvalidStateTransitionError`.

3. **Multi-Frame Touchdown Persistence**:
   - Transition to `LANDING_CONFIRMED` requires all touchdown criteria ($z \le 0.3\text{ m}$, $|v_z| \le 0.2\text{ m/s}$) to be satisfied continuously across $N \ge 10$ consecutive observation frames.

4. **Hierarchical Abort Dominance**:
   - Safety checks strictly dominate phase progression:
     $$\text{CRITICAL\_FAULT} \succ \text{ESTIMATOR} \succ \text{TARGET\_LOST} \succ \text{UNCERTAINTY} \succ \text{VELOCITY} \succ \text{ALIGNMENT}$$
   - Any active invariant breach instantly triggers `ABORTING` or `FAULT`.

5. **Latched Fault Policy**:
   - Critical faults and recovery timeouts trigger the terminal `FAULT` state and remain permanently latched until an explicit software reset.

## Consequences

* **Positive**:
  - Deterministic, explainable, and machine-readable landing decisions.
  - Sub-millisecond supervisory latency (~16 µs per evaluation cycle).
  - Robust protection against optical dropouts, covariance explosion, and excessive velocities.
  - 100% reproducible and testable offline via synthetic scenario simulation.

* **Negative / Trade-offs**:
  - Conservative safety thresholds may trigger aborts in turbulent conditions; tuning requires empirical flight testing.
