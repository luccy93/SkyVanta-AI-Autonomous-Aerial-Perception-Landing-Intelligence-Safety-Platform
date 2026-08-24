# SkyVanta AI — Volume 4 Architecture Specification
**Staged Landing-Pad Perception & 6-DoF PnP Pose Estimation**

---

## 1. Executive Summary

Volume 4 (V4) establishes the first spatial-perception layer of SkyVanta AI. It elevates the platform from **2D image-space tracking** to **calibrated 3D camera-relative spatial pose estimation ($T_{pad}^{cam} = [R \mid t]$)**.

Volume 4 answers the flight-critical spatial question:
> **"Where is the landing target relative to the camera in metric 3D space, what is its 3D orientation, and how trustworthy is that estimate?"**

### Core Capabilities Delivered in Volume 4:
1. **Calibrated Pinhole Camera Model (`CameraModel`)**: Enforces positive focal lengths, principal point bounding, non-finite coefficient rejection, pixel-to-ray casting, and 3D reprojection.
2. **Unified Landing Target Model (`LandingTarget`, `LandingPad`)**: Encapsulates 4-corner planar geometry, decoded marker ID, confidence, and timestamps independently of the underlying detector backend.
3. **Multi-Backend Fiducial Detection (`ArucoFiducialDetector`, `AprilTagFiducialDetector`, `MockFiducialDetector`)**: Extensible adapter interfaces with OpenCV ArUco (`DICT_6X6_250`, etc.) and AprilTag (`tag36h11`) support.
4. **Defensive Corner Validation (`CornerValidator`)**: Validates point count (exactly 4), finite values, duplicate vertex rejection, minimum enclosed pixel area (Shoelace formula), and strict quadrilateral convexity before feeding into PnP.
5. **Configurable Physical Target Geometry (`TargetGeometry`)**: Standardized 3D metric coordinate system in meters for square planar landing pads.
6. **Planar Perspective-n-Point Solver (`PnPPoseSolver`)**: Implements `cv2.SOLVEPNP_IPPE` (Infinitesimal Plane-based Pose Estimation) mathematically optimal for planar 4-point markers, with `ITERATIVE` and `RANSAC` fallback modes.
7. **Canonical Rotation Representations (`skyvanta.spatial.transform`)**: Internal rotation matrices and unit quaternions with Rodrigues vector and Euler angle conversions.
8. **Reprojection Error & Quality Assessment (`PoseQualityEvaluator`)**: Re-projects 3D object points to the image plane to compute RMS reprojection error and composite pose quality rating $[0.0, 1.0]$.
9. **Deterministic Synthetic Test Harness (`SyntheticPoseGenerator`)**: Generates ground-truth 3D poses and 2D pixel corners with controlled Gaussian noise for 100% offline verification.

---

## 2. Architecture & Pipeline Data Flow

```
Camera Frame (BGR)
       ↓
BaseFiducialDetector (ArUco / AprilTag / Mock)
       ↓
Detected LandingTarget (4 Corners in Pixels)
       ↓
CornerValidator (Area > 16px², Strict Convexity, Non-Collinear)
       ↓
TargetGeometry (Physical 3D Points in Target Frame: ±s/2)
       ↓
CameraModel (Matrix K, Distortion D)
       ↓
PnPPoseSolver (cv2.SOLVEPNP_IPPE)
       ↓
ProjectPoints Reprojection (RMS Error Computation)
       ↓
PoseQualityEvaluator (Reprojection + Area + Depth Score)
       ↓
PoseEstimateResult (Pose6D + Quality + Failure Diagnostics)
       ↓
Unified LandingPad Model
```

---

## 3. Detailed Component Specifications

### 3.1 Pinhole Camera Model (`CameraModel`)
* **Camera Matrix ($K$)**:
  $$K = \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}$$
* **Distortion Vector ($D$)**: $[k_1, k_2, p_1, p_2, k_3]$
* Validates $f_x > 0, f_y > 0$, $0 \le c_x \le \text{width}$, $0 \le c_y \le \text{height}$, and finite distortion coefficients.

### 3.2 Planar PnP Solver (`PnPPoseSolver`)
* **Solver Method**: `cv2.SOLVEPNP_IPPE` (Infinitesimal Plane-based Pose Estimation)
  - Specifically designed for planar 4-point configurations.
  - Resolves planar pose ambiguity analytically.
* **RMS Reprojection Error**:
  $$\text{RMS} = \sqrt{\frac{1}{4} \sum_{i=0}^3 \|\mathbf{p}_i^{\text{obs}} - \mathbf{p}_i^{\text{proj}}\|^2}$$
* **Depth Gating**: Enforces $z > \text{min\_depth\_m}$ (default: $0.05\text{m}$) and $z \le \text{max\_depth\_m}$ (default: $50.0\text{m}$).
* **Reprojection Gate**: Rejects poses with $\text{RMS} > \text{max\_reprojection\_error\_px}$ (default: $5.0\text{px}$).

### 3.3 6-DoF Pose Representation (`Pose6D`)
* **Translation**: $(x, y, z)$ in meters relative to camera optical frame ($X$: right, $Y$: down, $Z$: forward into scene).
* **Rotation**:
  - `rotation_matrix`: $3 \times 3$ orthonormal matrix $R \in \mathbb{SO}(3)$.
  - `quaternion`: Unit quaternion $(q_w, q_x, q_y, q_z)$ with $q_w \ge 0$.
  - `rvec`: Rodrigues vector $(r_x, r_y, r_z)$ in radians.
  - `euler_deg`: Tait-Bryan Euler angles $(\text{roll}, \text{pitch}, \text{yaw})$ in degrees.
* **Range**: $d = \sqrt{x^2 + y^2 + z^2}$ in meters.
* **Quality & Validation**: `pose_quality` $[0.0, 1.0]$, `is_valid: bool`, `reprojection_error_rms: float`.

---

## 4. Configuration Reference

```yaml
landing_target:
  enabled: true
  detector_type: "aruco" # "aruco", "apriltag", or "mock"
  camera:
    image_width: 1280
    image_height: 720
    fx: 1000.0
    fy: 1000.0
    cx: 640.0
    cy: 360.0
    distortion_coefficients: [0.0, 0.0, 0.0, 0.0, 0.0]
  april_tag:
    family: "tag36h11"
    tag_size_m: 0.20
    threads: 2
    quad_decimate: 1.0
  aruco:
    dictionary: "DICT_6X6_250"
    marker_size_m: 0.20
    adaptive_thresh_win_size_min: 3
    adaptive_thresh_win_size_max: 23
    adaptive_thresh_win_size_step: 10
  pnp:
    solver: "IPPE"
    max_reprojection_error_px: 5.0
    min_depth_m: 0.05
    max_depth_m: 50.0
  quality:
    max_reproj_error_for_zero_quality: 8.0
    min_corner_area_px: 100.0
```

---

## 5. Verification & Test Coverage

* **112 Automated Tests Passing (100% Pass Rate)**:
  - `test_camera_calibration.py`: Intrinsics creation, validation, principal point bounds, ray casting, and 3D projection.
  - `test_fiducial_detection.py`: Mock, ArUco, and AprilTag detector execution and factory instantiation.
  - `test_corner_validation.py`: Convexity, duplicate vertex rejection, minimum area, and non-finite checks.
  - `test_target_geometry.py`: 3D object coordinate definitions centered at $(0, 0, 0)$.
  - `test_pnp_solver.py`: Pure translation, 3D rotations, noisy pixel recovery ($\sigma=0.5\text{px}$), depth gates, and reprojection error gates.
  - `test_rotation_transforms.py`: Roundtrip conversions between Rodrigues, rotation matrix, unit quaternion, and Euler angles.
  - `test_pose_quality.py`: Transparent quality formula evaluation under nominal and degraded conditions.
  - `test_landing_pad_integration.py`: End-to-end synthetic pipeline validation.

---

## 6. Known Subsystem Boundaries & Limitations

### Volume 4 Provides:
- Camera-relative 6-DoF pose ($T_{pad}^{cam}$).
- Fiducial marker identification and corner extraction.
- Geometric reprojection error and pose quality scoring.
- Pinhole camera intrinsic calibration.

### Volume 4 Strictly Excludes (Handled in V5+):
- World-frame navigation coordinate transformations ($T_{pad}^W = T_{body}^W T_{cam}^{body} T_{pad}^{cam}$) (Volume 5).
- IMU, LiDAR, Barometer, and GPS sensor fusion (Volume 6).
- 15-State Error-State Kalman Filter (ESEKF) (Volume 6).
- Flight control commands, FSM landing intelligence, and safety overrides (Volume 7 & 8).
