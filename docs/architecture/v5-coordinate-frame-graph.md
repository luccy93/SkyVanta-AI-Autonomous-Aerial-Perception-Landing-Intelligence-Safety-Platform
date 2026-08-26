# SkyVanta AI — Volume 5 Coordinate Frame Graph & Conventions

---

## 1. Coordinate Frames Definition & Semantics

| Frame Identifier | Standard Notation | Convention | Origin / Reference | Axis Definition |
| :--- | :--- | :--- | :--- | :--- |
| **`CAMERA`** | $\mathcal{F}_C$ | Optical / Pinhole | Camera optical center (pinhole) | $+X$: Right along sensor rows<br>$+Y$: Down along sensor columns<br>$+Z$: Forward optical depth axis |
| **`BODY`** | $\mathcal{F}_B$ | NED / Aircraft Body | Drone center of mass (CoM) | $+X$: Forward along aircraft nose<br>$+Y$: Right along starboard wing<br>$+Z$: Down toward ground |
| **`LANDING_PAD`** | $\mathcal{F}_P$ | Planar Target | Physical marker centroid | $+X$: Right along marker horizontal<br>$+Y$: Down along marker vertical<br>$+Z$: Normal into landing pad surface |
| **`WORLD`** | $\mathcal{F}_W$ | Inertial Navigation (ENU) | Takeoff point / Geodetic origin | $+X$: East<br>$+Y$: North<br>$+Z$: Up (Altitude $\ge 0$, gravity $-Z$) |

> **Note on Aviation Standards**: The simulation environment and inertial state estimation operate in local **ENU** ($+Z$ Up). When interfacing with external aviation autopilots that use **NED** ($+Z$ Down), use explicit platform conversion utilities `skyvanta.spatial.transform.enu_to_ned_*` and `ned_to_enu_*`.

---

## 2. Directed Frame Graph Topology

```
                  [ WORLD (Inertial Navigation) ]
                                 |
                                 | (Future V6: GPS / VIO / SLAM)
                                 v
                     [ BODY (Aircraft CoM) ]
                                 |
                                 | (Static Extrinsic: T_body_camera)
                                 v
                    [ CAMERA (Optical Center) ]
                                 |
                                 | (Dynamic Vision Perception: T_camera_pad)
                                 v
                     [ LANDING_PAD (Target) ]
```

---

## 3. Mathematical Notation Standards

Throughout SkyVanta AI, spatial transforms follow standard active transformation conventions:

* **$T_{\text{target}\_\text{source}}$ (or $T_{\text{target}}^{\text{source}}$)**: Homogeneous transform matrix mapping a 3D point $\mathbf{p}_{\text{source}}$ expressed in the source coordinate frame into the target coordinate frame:
  $$\mathbf{p}_{\text{target}} = \mathbf{R} \mathbf{p}_{\text{source}} + \mathbf{t}$$
* **Composition Chain**:
  $$T_{B}^{P} = T_{B}^{C} \times T_{C}^{P}$$
  where $T_{B}^{C}$ is the static Body-to-Camera extrinsic, and $T_{C}^{P}$ is the dynamic Camera-to-Pad vision estimate.

---

## 4. World-Frame Disconnection Invariant

1. The `WORLD` coordinate frame is formally declared and defined as a standard node in the Frame Graph.
2. The directed edge from `BODY` to `WORLD` ($T_{\text{world}\_\text{body}}$) is explicitly initialized as **`UNAVAILABLE`** until an external sensor driver or state estimator registers an authentic measurement.
3. If an upstream caller queries a world-relative pose without an active world reference, the platform returns:
   - `is_valid = False`
   - `is_world_relative = False`
   - `pose = None`
   - `failure_reason = "WORLD frame reference is unavailable (no GPS, SLAM, or external visual odometry registered)"`
4. The system strictly prohibits using $(0, 0, 0)$ or identity matrix as a default world estimate.
