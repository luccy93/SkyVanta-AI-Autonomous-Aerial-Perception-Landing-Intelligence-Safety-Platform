# ADR-0008: Digital Twin, Advanced Simulation and Scenario Validation Architecture

## Status
**ACCEPTED** (2026-08-25)

## Context
Deploying autonomous landing software on real physical aerial systems involves substantial flight test costs, environmental variability, and safety risks.
To validate full-stack closed-loop performance prior to field operations, an engineering-grade Digital Twin simulation framework is required.

Key requirements:
1. End-to-end integration connecting perception, tracking, 6-DoF pose, spatial transforms, 15-state ESEKF sensor fusion, landing intelligence, and flight command interfaces.
2. Realistic continuous 6-DoF rigid body kinematics, aerodynamic drag, and atmospheric wind turbulence.
3. Deterministic fault injection for optical dropouts, sensor noise, and platform motion.
4. Quantitative statistical metrics for estimator consistency, touchdown accuracy, and abort preemption.

## Decision

1. **Closed-Loop Simulation Architecture**:
   - `DigitalTwinEngine` integrates continuous vehicle dynamics with synthetic sensor models (Camera, IMU) and executes the entire SkyVanta software pipeline in a closed loop.

2. **Modular Environment & Sensor Noise Models**:
   - `EnvironmentalConditions` generates baseline wind vectors and sinusoidal gust turbulence.
   - `SyntheticSensorSuite` generates calibrated camera projections with pixel noise and IMU specific force/angular rate packets.

3. **Deterministic Fault Injection Framework**:
   - `FaultSchedule` injects optical occlusions, sensor noise spikes, and timing delays without modifying production code paths.

4. **Standardized Scenario Catalog & Batch Harness**:
   - `ScenarioCatalog` defines standard regression benchmarks.
   - `BatchScenarioRunner` automates execution across randomized seeds and computes statistical metrics (NEES consistency, touchdown RMSE, abort compliance).

## Consequences

* **Positive**:
  - Full-stack reproducibility and automated regression validation in continuous integration.
  - Zero hardware risk during testing of hazardous edge cases (e.g. high crosswinds, sudden optical loss).
  - Quantitative verification of 15-state ESEKF estimation error against true physical ground truth.

* **Negative / Trade-offs**:
  - Simplified aerodynamic models do not capture complex aerodynamic ground effect or rotor blade wash interactions.
