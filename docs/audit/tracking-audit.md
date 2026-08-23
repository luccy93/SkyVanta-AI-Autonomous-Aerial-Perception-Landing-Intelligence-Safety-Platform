# SkyVanta AI — Target Tracking Architecture Audit (V0)

## 1. Tracking Components Audit

```
+---------------------------------------------------------------------------------------------------+
|                                  CURRENT TRACKING PIPELINE (main.py)                              |
+---------------------------------------------------------------------------------------------------+

   [ Detections from YOLO / Motion ]
                  |
                  v
       [ _pick_best() Function ] ---> IoU Overlap > 0.1 Check (Single-target greedy selection)
                  |
                  v
       [ KalmanBox2D (cv2.KalmanFilter) ]
         - State Vector: [cx, cy, w, h, vx, vy, vw, vh]^T
         - Constant Velocity Motion Model
         - Measurement: [cx, cy, w, h]^T
                  |
                  v
       [ Vec2EuroFilter + OneEuroFilter ]
         - Adaptive low-pass filter on smoothed center and size
                  |
                  v
       [ Jump Distance Check ]
         - If delta > 4.5% of diagonal, clear trail (rejects abrupt track teleportation)
                  |
                  v
       [ 5-State FSM State Update ]
         - Transitions: SEARCHING <-> ACQUIRED <-> TRACKING <-> LOCKED <-> APPROACHING
```

---

## 2. Detailed Tracking Audit Matrix

| Metric / Aspect | Current Repository Implementation | Algorithmic Evaluation | Status |
| :--- | :--- | :--- | :--- |
| **State Vector** | $X = [cx, cy, w, h, \dot{cx}, \dot{cy}, \dot{w}, \dot{h}]^T \in \mathbb{R}^8$ | 2D pixel space box coordinates. Does not model 3D metric position or orientation. | **IMPLEMENTED** (2D Only) |
| **Filter Formulation** | `cv2.KalmanFilter(8, 4)` | Standard linear discrete Kalman filter with fixed process/measurement covariance ($Q=0.01 I, R=0.1 I$). | **IMPLEMENTED** |
| **Post-Filtering** | `OneEuroFilter` (Cutoff: 1.0Hz, $\beta = 0.015$) | Effectively eliminates high-frequency pixel jitter without introducing noticeable phase lag. | **IMPLEMENTED** |
| **Data Association** | `_pick_best()`: Greedy single-pair IoU match | Works only for single-target tracking. Fails if multiple drones or distractor targets exist in FOV. | **PROTOTYPE ONLY** |
| **Track Lifecycle** | `hits` counter, `frames_since_hit` counter | Track confirmed on first hit; marked lost after 45 missed frames ($1.5\text{s}$ at 30 FPS). | **IMPLEMENTED** |
| **Occlusion Recovery** | Kalman prediction without measurement update | Propagates constant velocity model during dropouts. Clears trail if position jumps $> 4.5\%$ screen diag. | **PARTIAL** |
| **Velocity Estimation**| Implicit in Kalman filter internal states | Not exported or used for metric guidance or dynamic pad velocity estimation. | **PROTOTYPE** |
| **Multi-Target Support**| Single track instance (`DroneTracker`) | Hardcoded to track exactly one target at a time. No track ID manager or global track pool. | **NOT IMPLEMENTED** |

---

## 3. Recommended Tracking Evolution (Volumes 3 & 6)
1. **Multi-Target Data Association**: Replace greedy single IoU with **Hungarian Algorithm (Munkres)** operating on a cost matrix combining bounding box IoU, visual feature embedding cosine similarity, and Mahalanobis distance.
2. **Transition from 2D Pixel Tracking to 3D Metric Tracking**:
   * Current: Tracks $(cx, cy, w, h)$ in pixel coordinates.
   * Target: Track relative metric 3D position $(x, y, z)$ and orientation $(q)$ in the **15-State Error-State EKF**.
