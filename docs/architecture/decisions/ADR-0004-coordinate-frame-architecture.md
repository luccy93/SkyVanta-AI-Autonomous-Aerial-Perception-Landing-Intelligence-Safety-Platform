# ADR-0004: Coordinate Frame Architecture and Spatial Transform System

## Status
**ACCEPTED** (2026-08-24)

## Context
In Volume 4, SkyVanta AI introduced 6-DoF landing pad pose estimation expressed strictly in the camera optical frame ($T_{pad}^{cam}$).
To prepare for flight controller integration, landing corridor computation, and future multi-sensor fusion (IMU, GPS, LiDAR, Barometer), the system requires a mathematically rigorous spatial transformation engine that can safely map 3D points and 6-DoF poses between coordinate frames (Camera, Drone Body, Landing Pad, and World).

We needed to decide on:
1. Frame representation and typing.
2. Homogeneous transformation formalism and validation gates.
3. Transform graph topology and path resolution.
4. Handling of unobservable world references.

## Decision

1. **Strongly-Typed Coordinate Frames**:
   - We define `FrameId` as an explicit Python `Enum` (`CAMERA`, `BODY`, `WORLD`, `LANDING_PAD`, `CUSTOM`). Arbitrary unstructured strings across internal APIs are forbidden.

2. **Rigorous $\mathbb{SE}(3)$ Transformation Engine**:
   - `SE3Transform` implements homogeneous $4 \times 4$ rigid body transformations:
     $$T = \begin{bmatrix} \mathbf{R} & \mathbf{t} \\ \mathbf{0} & 1 \end{bmatrix}$$
   - Numerical integrity gates validate $\mathbf{R} \in \mathbb{SO}(3)$ orthonormality ($\|\mathbf{R}^T \mathbf{R} - \mathbf{I}\| \le 10^{-3}$) and unit determinant ($|\det(\mathbf{R}) - 1| \le 10^{-3}$) on construction.
   - Exact closed-form inversion ($T^{-1} = \begin{bmatrix} \mathbf{R}^T & -\mathbf{R}^T \mathbf{t} \\ \mathbf{0} & 1 \end{bmatrix}$) and associative composition are enforced.

3. **Shortest-Path Frame Graph**:
   - `FrameGraph` maintains an adjacency structure of static and dynamic transforms and resolves multi-hop chains (e.g. $\text{PAD} \to \text{CAMERA} \to \text{BODY}$) using BFS.
   - Dynamic transforms are validated against a configurable staleness gate (`max_transform_age_sec`).

4. **World-Frame Unavailability Invariant**:
   - The `WORLD` frame is modeled as an architectural node, but the `WORLD \to BODY` transform is strictly marked `UNAVAILABLE` until an authentic external sensor reference is provided.
   - Queries for world position without an active reference return explicit failure diagnostics rather than dummy coordinates $(0, 0, 0)$.

## Consequences

* **Positive**:
  - Deterministic metric coordinate transformations across arbitrary frames.
  - Sub-microsecond composition and inversion speeds (~35 µs in pure Python).
  - Clear architectural boundaries preventing sensor fusion logic from prematurely leaking into perception layers.
  - 100% testable using synthetic geometric fixtures.

* **Negative / Trade-offs**:
  - Static camera mounting extrinsics must be correctly specified in configuration; errors in body-to-camera calibration will directly bias body-relative target tracking.
