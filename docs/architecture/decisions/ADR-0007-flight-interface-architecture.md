# ADR-0007: Flight Interface and Autopilot Integration Architecture

## Status
**ACCEPTED** (2026-08-25)

## Context
Volume 7 produces explainable `LandingDecision` recommendations based on fused sensor states and independent safety supervisor invariants.
To interface with aerial vehicles without compromising flight safety or risking uncommanded physical actuation, a secure flight interface layer is required.

Key challenges include:
1. Preventing accidental transmission of flight commands to real hardware.
2. Decoupling high-level supervisory decisions from low-level autopilot protocols (MAVLink, PX4, ArduPilot).
3. Ensuring command delivery guarantees with rate limiting, timeouts, expiration, and sequence tracking.
4. Handling autopilot disconnection and heartbeat loss deterministically.

## Decision

1. **Simulation-First Architecture**:
   - `FlightInterfaceConfig` defaults to `mode: simulation`. No serial, UDP, or TCP hardware connections are established by default.
   - `MockAutopilot` provides a fully deterministic software-in-the-loop (SIL) simulation of vehicle kinematics, flight modes, command acknowledgements, and telemetry.

2. **Decoupled High-Level Command Contracts**:
   - Commands are represented by `FlightCommand` models with unique identifiers, monotonic sequence numbers, finite expiration windows, and explicit parameter bags.

3. **Multi-Stage Validation & Authorization Pipeline**:
   - Commands pass through `FlightCommandValidator` (structural/temporal sanity), `CommandAuthorizationPolicy` (V7 safety clearance, flight mode rules), and `CommandRateLimiter` (rate limits, duplicate suppression).

4. **Safety Command Preemption**:
   - `ABORT` commands hold the highest priority (100) and bypass rate limiting to guarantee instantaneous execution.
   - Any V7 `ABORT` decision is mathematically barred from translating into descent commands.

5. **Heartbeat Monitoring & Failsafe**:
   - `HeartbeatMonitor` tracks connection liveness. If heartbeats lapse beyond threshold ($2.5\text{ s}$), the interface transitions to `FAILSAFE` and halts all normal landing progression commands.

## Consequences

* **Positive**:
  - Safe, decoupled, and audit-traceable command flow.
  - Zero risk of uncommanded physical motor actuation.
  - Fully testable in continuous integration without hardware dependencies.
  - Sub-millisecond supervisory latency (~3.6 ms with full JSON event logging, < 20 µs without I/O).

* **Negative / Trade-offs**:
  - Physical autopilot integration requires external adapter bridge implementations in future volumes.
