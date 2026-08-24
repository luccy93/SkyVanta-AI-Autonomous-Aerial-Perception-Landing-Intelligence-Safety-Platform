# SkyVanta AI — Volume 5 Architecture Specification
**Spatial Coordinate Transformation & Localization Engine**

---

## 1. Executive Summary

Volume 5 (V5) establishes the formal spatial coordinate-frame and transform graph system for SkyVanta AI. It answers the fundamental robotics localization question:

> **"Given a 3D pose or measurement expressed in one coordinate frame (e.g. camera-relative landing pad detection), how do we safely, rigorously, and deterministically transform it into other critical coordinate frames (e.g. drone body frame or world navigation frame)?"**

### Core Capabilities Delivered in Volume 5:
1. **Strongly-Typed Coordinate Frames (`FrameId`)**: Explicit, discrete frame identifiers (`CAMERA`, `BODY`, `WORLD`, `LANDING_PAD`, `CUSTOM`) eliminating string typos and ambiguous frames.
2. **Formal $\mathbb{SE}(3)$ Transformation Abstraction (`SE3Transform`)**:
   $$T = \begin{bmatrix} \mathbf{R} & \mathbf{t} \\ \mathbf{0}_{1 \times 3} & 1 \end{bmatrix} \in \mathbb{SE}(3)$$
   Strictly enforces $\mathbf{R} \in \mathbb{SO}(3)$ orthonormality ($\mathbf{R}^T \mathbf{R} \approx \mathbf{I}$), proper rotation ($\det(\mathbf{R}) \approx +1$), finite translation in meters, composition ($T_1 \times T_2$), and exact matrix inversion ($T^{-1} = \begin{bmatrix} \mathbf{R}^T & -\mathbf{R}^T \mathbf{t} \\ \mathbf{0} & 1 \end{bmatrix}$).
3. **Coordinate Frame Graph & Transform Registry (`FrameGraph`)**: Directed multigraph resolving shortest transform chains via BFS, automatically applying forwards and inverse transforms, and detecting disconnected or stale dynamic transforms.
4. **Static Extrinsics Modeling (`CameraExtrinsicsConfig`)**: Configurable rigid body-to-camera mounting geometry ($T_{\text{body}\_\text{camera}}$).
5. **V4-to-V5 Integration Pipeline (`SpatialLocalizationService`)**: Seamlessly composes V4 landing pad perception ($T_{\text{camera}\_\text{pad}}$) with body extrinsics ($T_{\text{body}\_\text{camera}}$) to produce metric body-frame targets ($T_{\text{body}\_\text{pad}}$).
6. **Explicit World-Frame Unavailability Contract**: Strict architectural rule guaranteeing that world localization requests fail transparently with `is_world_relative=False` unless a valid external world reference (e.g. GPS, SLAM, or VIO) is registered. Zero vector $(0,0,0)$ or identity are **never** fabricated.
7. **Spatial Uncertainty & Covariance Contracts (`SpatialUncertainty`)**: Clean extensibility model ready for future Volume 6 Kalman sensor fusion without fabricating synthetic covariances.

---

## 2. Spatial Transformation Pipeline

```
V4 PoseEstimate (T_camera_pad)
             ↓
Frame Graph (Shortest-Path BFS)
             ↓
Extrinsics Lookup (T_body_camera)
             ↓
SE(3) Composition: T_body_pad = T_body_camera × T_camera_pad
             ↓
Coordinate & Quaternion Conversion
             ↓
World Reference Validation
             ↓
SpatialLocalizationResult (Body Pose / World Unavailable Reason)
```

---

## 3. Detailed Component Specifications

### 3.1 SE(3) Transform Abstraction (`SE3Transform`)
* **Matrix Representation**: Homogeneous $4 \times 4$ matrix $T \in \mathbb{SE}(3)$.
* **Orthonormality Gate**: Validates $\|\mathbf{R}^T \mathbf{R} - \mathbf{I}\|_\infty \le 10^{-3}$ and $|\det(\mathbf{R}) - 1| \le 10^{-3}$.
* **Inversion**:
  $$T^{-1} = \begin{bmatrix} \mathbf{R}^T & -\mathbf{R}^T \mathbf{t} \\ \mathbf{0} & 1 \end{bmatrix}$$
* **Composition**:
  $$T_{A \to C} = T_{A \to B} \times T_{B \to C} = \begin{bmatrix} \mathbf{R}_{AB} \mathbf{R}_{BC} & \mathbf{R}_{AB} \mathbf{t}_{BC} + \mathbf{t}_{AB} \\ \mathbf{0} & 1 \end{bmatrix}$$
* **Point Transformation**:
  $$\mathbf{p}_{\text{target}} = \mathbf{R} \mathbf{p}_{\text{source}} + \mathbf{t}$$

### 3.2 Frame Graph (`FrameGraph`)
* Maintains a directed graph of registered static and dynamic coordinate frames.
* Computes shortest path between arbitrary source and target frames.
* Evaluates dynamic transform timestamp age against `max_transform_age_sec`.
* Raises `DisconnectedFrameError` when no connected path exists.

### 3.3 Spatial Localization Service (`SpatialLocalizationService`)
* Manages the lifecycle of static extrinsics and dynamic vision measurements.
* Exposes `localize_target(pose_result, target_frame=FrameId.BODY) -> SpatialLocalizationResult`.
* Exposes `register_world_reference(transform_world_body)` for future localization sensors.

---

## 4. Configuration Schema

```yaml
spatial:
  enabled: true
  default_world_frame: "WORLD"
  default_body_frame: "BODY"
  default_camera_frame: "CAMERA"
  default_pad_frame: "LANDING_PAD"
  camera_extrinsics:
    enabled: true
    parent_frame: "BODY"
    child_frame: "CAMERA"
    translation_m: [0.0, 0.0, 0.0]
    rotation_rpy_deg: [0.0, 0.0, 0.0]
  max_transform_age_sec: 0.5
  tolerance_orthonormal: 0.0001
  tolerance_det: 0.0001
```

---

## 5. Subsystem Boundaries & Strict Limitations

### Volume 5 Provides:
- Strongly typed coordinate frames.
- $\mathbb{SE}(3)$ transformations and compositions.
- Camera-to-body extrinsics resolution.
- Multi-frame pose and point transformations.
- Explicit world-frame availability contracts.

### Volume 5 Strictly Excludes (Handled in V6+):
- IMU, LiDAR, Barometer, and GPS drivers.
- 15-State Error-State Kalman Filter (ESEKF) sensor fusion.
- Visual Odometry and SLAM estimators.
- Real-time flight commands, landing controllers, and safety state machines.
