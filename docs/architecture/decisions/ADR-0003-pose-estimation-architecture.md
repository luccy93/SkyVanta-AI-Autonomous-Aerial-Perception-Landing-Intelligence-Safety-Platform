# ADR-0003: 6-DoF Perspective-n-Point (PnP) Pose Estimation Architecture

## Status
**ACCEPTED** (2026-08-24)

## Context
In Volumes 1–3, SkyVanta AI operated exclusively in 2D image coordinates (bounding boxes, pixel centroids, optical flow vectors, and visual heuristics). Safe autonomous drone landing requires precise metric 3D relative positioning and orientation ($T_{pad}^{cam} = [R \mid t]$) with quantifiable uncertainty.

We needed to decide on:
1. The mathematical solver algorithm for 4-corner planar landing targets.
2. The internal canonical rotation representation.
3. The fiducial detector abstraction architecture.
4. Validation and error handling mechanisms to reject degenerate poses before they reach future state estimation filters.

## Decision

1. **Solver Algorithm**:
   - We adopt **`cv2.SOLVEPNP_IPPE` (Infinitesimal Plane-based Pose Estimation)** as the primary solver for planar fiducials.
   - *Rationale*: For planar 4-point markers, IPPE is mathematically closed-form, faster, and resolves planar pose ambiguity analytically without the local minima traps of generic non-linear optimization (`SOLVEPNP_ITERATIVE`).
   - We retain `SOLVEPNP_ITERATIVE` and `SOLVEPNP_RANSAC` as configurable fallback options for non-planar or multi-point configurations.

2. **Rotation Representation**:
   - The canonical internal rotation representations are $3 \times 3$ orthonormal rotation matrices $\mathbf{R} \in \mathbb{SO}(3)$ and unit quaternions $\mathbf{q} = (q_w, q_x, q_y, q_z)$.
   - Rodrigues vectors ($\mathbf{r}$) and Tait-Bryan Euler angles $(\text{roll}, \text{pitch}, \text{yaw})$ are computed analytically on demand for OpenCV PnP interfacing and telemetry HUD rendering.

3. **Multi-Backend Fiducial Detection Abstraction**:
   - `BaseFiducialDetector` provides a clean ABC interface.
   - `ArucoFiducialDetector` interfaces with `cv2.aruco`.
   - `AprilTagFiducialDetector` interfaces with `pupil_apriltags` or OpenCV's native AprilTag dictionary fallback.
   - `MockFiducialDetector` provides deterministic synthetic target generation for 100% reproducible offline CI/CD testing.

4. **Defensive Validation & Pose Quality Gating**:
   - `CornerValidator` guarantees quadrilateral validity (point count == 4, finite coordinates, minimum area via Shoelace formula, and strict convexity via cross-product signs) *before* PnP invocation.
   - Reprojection error is calculated using `cv2.projectPoints`, and poses exceeding `max_reprojection_error_px` (default: 5.0px) or having non-positive depth ($z \le 0$) are strictly flagged invalid.
   - `PoseQualityEvaluator` computes a transparent $[0.0, 1.0]$ composite quality metric.

## Consequences

* **Positive**:
  - Sub-millimeter translation precision on clean planar fiducials.
  - Zero external hardware or IMU dependencies required for relative pose estimation.
  - Complete testability with deterministic offline synthetic generators.
  - Strict separation of concerns between 2D tracking and 3D spatial estimation.

* **Negative / Trade-offs**:
  - Camera intrinsic calibration must be known and accurate; uncalibrated or distorted lenses will degrade metric translation accuracy.
  - High camera tilt angles relative to the landing pad ($> 75^\circ$) can compress pixel area and increase reprojection error.
