# SkyVanta AI — Volume 4 Coordinate System Conventions

---

## 1. Executive Summary

Volume 4 marks the critical transition from **2D image-space perception (pixels)** to **3D camera-relative metric pose estimation (meters, radians)**. To maintain mathematical consistency and prevent frame transformation errors across perception, state estimation, and future sensor fusion layers, SkyVanta AI defines standard, explicit coordinate frames.

---

## 2. Coordinate Frames Definition

```
                       [ +Y_cam: Down ]
                              |
                              |
         [ +X_cam: Right ]----+----> (Optical Axis: +Z_cam Forward)
                             /
                            /
                           v
```

### 2.1 Camera Optical Frame ($\mathcal{F}_C$)
The standard OpenCV pinhole camera optical frame:
* **Origin ($O_C$)**: Camera optical projection center (pinhole).
* **$+X_C$ (Right)**: Points to the right along image sensor horizontal scanlines.
* **$+Y_C$ (Down)**: Points downwards along image sensor vertical scanlines.
* **$+Z_C$ (Forward / Depth)**: Points directly forward into the scene along the optical axis.
* **Handedness**: Right-handed Cartesian coordinate system ($\hat{x} \times \hat{y} = \hat{z}$).

### 2.2 Marker / Landing Target Frame ($\mathcal{F}_P$)
The local coordinate frame attached to the physical planar fiducial landing marker:
* **Origin ($O_P$)**: Geometric centroid of the physical square marker ($Z=0$).
* **$+X_P$ (Marker Right)**: Tangent to the marker surface, pointing from center to right edge.
* **$+Y_P$ (Marker Down)**: Tangent to the marker surface, pointing from center to bottom edge.
* **$+Z_P$ (Marker Normal)**: Normal vector pointing into the landing pad surface.
* **Corner Ordering Convention** (Looking directly at the front face of the marker):
  1. **Corner 0 (Top-Left)**: $\mathbf{P}_0 = \left[-\frac{s}{2}, -\frac{s}{2}, 0\right]^T$
  2. **Corner 1 (Top-Right)**: $\mathbf{P}_1 = \left[+\frac{s}{2}, -\frac{s}{2}, 0\right]^T$
  3. **Corner 2 (Bottom-Right)**: $\mathbf{P}_2 = \left[+\frac{s}{2}, +\frac{s}{2}, 0\right]^T$
  4. **Corner 3 (Bottom-Left)**: $\mathbf{P}_3 = \left[-\frac{s}{2}, +\frac{s}{2}, 0\right]^T$
  Where $s$ is the physical marker side length in meters (`marker_size_m`).

---

## 3. Transformation Formulation

The 6-DoF transformation $[R \mid \mathbf{t}]$ solved by Perspective-n-Point maps 3D points expressed in the **Target Frame ($\mathcal{F}_P$)** into the **Camera Optical Frame ($\mathcal{F}_C$)**:

$$\mathbf{P}_C = \mathbf{R}_{P}^{C} \mathbf{P}_P + \mathbf{t}_{P}^{C}$$

Where:
* $\mathbf{P}_P \in \mathbb{R}^3$: 3D metric coordinate of a marker point in target frame ($\mathcal{F}_P$).
* $\mathbf{P}_C = [x, y, z]^T \in \mathbb{R}^3$: 3D metric coordinate of the same point in camera frame ($\mathcal{F}_C$).
* $\mathbf{t}_{P}^{C} = [t_x, t_y, t_z]^T$: Translation vector representing the position of the marker center in camera frame coordinates (meters).
* $\mathbf{R}_{P}^{C} \in \mathbb{SO}(3)$: $3 \times 3$ orthonormal rotation matrix ($R^T R = I, \det(R) = +1$).

---

## 4. Angular Representations & Conventions

1. **Rodrigues Vector ($\mathbf{r} \in \mathbb{R}^3$)**:
   $$\mathbf{r} = \theta \mathbf{u}, \quad \|\mathbf{u}\| = 1, \quad \theta = \|\mathbf{r}\| \text{ (radians)}$$
2. **Unit Quaternion ($\mathbf{q} = [q_w, q_x, q_y, q_z]^T$)**:
   $$\|\mathbf{q}\|^2 = q_w^2 + q_x^2 + q_y^2 + q_z^2 = 1.0, \quad q_w \ge 0$$
3. **Tait-Bryan Euler Angles (Z-Y-X Sequence)**:
   * $\text{Yaw} (\psi)$: Rotation around $+Z_C$ axis.
   * $\text{Pitch} (\theta)$: Rotation around $+Y_C$ axis.
   * $\text{Roll} (\phi)$: Rotation around $+X_C$ axis.
   * Internal canonical representation is $\mathbf{R} \in \mathbb{SO}(3)$ and $\mathbf{q}$. Euler angles are provided exclusively for telemetry display and human inspection.

---

## 5. Units & Standards Matrix

| Quantity | Variable | Unit | Representation / Type |
| :--- | :--- | :--- | :--- |
| Translation ($X, Y, Z$) | $t_x, t_y, t_z$ | Meters ($\text{m}$) | `float64` |
| Range Distance | $d$ | Meters ($\text{m}$) | `float64` |
| Marker Side Length | $s$ | Meters ($\text{m}$) | `float64` |
| Image Coordinates ($u, v$) | $u, v$ | Pixels ($\text{px}$) | `float64` |
| Reprojection Error | $\text{RMS}$ | Pixels ($\text{px}$) | `float64` |
| Rotation Vector | $\mathbf{r}$ | Radians ($\text{rad}$) | `Tuple[float, float, float]` |
| Euler Angles (Telemetry) | $\phi, \theta, \psi$ | Degrees ($^\circ$) | `Tuple[float, float, float]` |
| Pose Quality | $Q$ | Normalized $[0.0, 1.0]$ | `float64` |
