# SkyVanta AI — Computer Vision Implementation Audit (V0)

## 1. Computer Vision Inventory & Capability Status

| CV Component | File & Class/Function | Algorithmic Approach | Input Data | Output Data | Implementation Status | Level | Reusability Rating |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **YOLO Detector** | `main.py`<br>`YoloDroneDetector` | Ultralytics YOLOv8-Nano (`yolov8n.pt`) filtering proxy classes (`bird`, `airplane`, `kite`, `frisbee`) | BGR Image ($640 \times 640$) | BBoxes `(x1, y1, x2, y2, conf)` | **PROTOTYPE / DEMO** | Level A | **REFACTOR**: Replace COCO weights with custom drone/pad weights |
| **Motion Detector** | `main.py`<br>`MotionContrastDetector` | `MOG2` background subtractor + `Farneback` dense optical flow + `Canny` edge filter | Grayscale / BGR Image | Candidate BBoxes with edge scores | **IMPLEMENTED** | Level A | **KEEP**: Excellent fallback for non-semantic motion cues |
| **Optical Flow** | `main.py`<br>`MotionContrastDetector` | `cv2.calcOpticalFlowFarneback` (Dense flow on whole image) | Consecutive grayscale frames | 2-channel flow velocity matrix | **PROTOTYPE** | Level A | **REFACTOR**: Farneback is CPU-heavy; switch to Sparse LK |
| **Target Association** | `main.py`<br>`DroneTracker._pick_best` | IoU overlap thresholding ($> 0.1$) between YOLO and motion boxes | YOLO boxes, Motion boxes | Single prioritized bounding box | **PROTOTYPE** | Level A | **REPLACE LATER**: Upgrade to Hungarian Assignment algorithm |
| **2D Bounding Box KF** | `main.py`<br>`KalmanBox2D` | Linear constant-velocity Kalman Filter (8 state, 4 measurement) | BBox center & dimensions | Predicted / corrected $(cx, cy, w, h)$ | **IMPLEMENTED** | Level A | **KEEP / WRAP**: Good 2D filter, needs metric 3D counterpart |
| **One Euro Filter** | `main.py`<br>`OneEuroFilter`, `Vec2EuroFilter` | First-order adaptive low-pass filter with velocity-dependent cutoff | Scalar / 2D point, timestamp | Filtered jitter-free point | **IMPLEMENTED** | Level A | **KEEP**: Highly reusable for UI and trajectory smoothing |
| **Perspective Corridor**| `main.py`<br>`ApproachCorridor` | 2D trapezoidal perspective mesh anchored to drone center and virtual pad | Drone center, size, timestamp | Corner points (`apex, tl, tr, bl, br`) | **VISUALIZATION ONLY** | Level A | **REFACTOR**: Anchor to real metric PnP 3D pose |
| **HUD Compositor** | `main.py`<br>`HUDRenderer` | Multi-layer OpenCV drawing (alpha blending, dashed lines, glow) | Frame, Track, Telemetry, Corridor | Composite BGR HUD Frame | **IMPLEMENTED** | Level A | **KEEP / WRAP**: Excellent visual HUD for GCS video stream |
| **Fiducial Tag Detection**| *None* | AprilTag 3 / ArUco | *N/A* | *N/A* | **NOT IMPLEMENTED** | Level A | **PLANNED**: Mandatory for Level 1 precision landing |
| **PnP 6-DoF Pose Solver**| *None* | `cv2.solvePnP` / `SOLVEPNP_IPPE` | *N/A* | *N/A* | **NOT IMPLEMENTED** | Level A | **PLANNED**: Mandatory for metric 3D localization |
| **Camera Calibration** | *None* | Checkerboard / Charuco solver | *N/A* | *N/A* | **NOT IMPLEMENTED** | Level A | **PLANNED**: Mandatory for metric distance and PnP |

---

## 2. Technical Findings & Limitations

### 2.1 Object Detection
* **Issue**: The current implementation relies on standard COCO classes (`airplane`, `bird`, `kite`, `frisbee`) at an extremely low confidence threshold ($0.08$) as proxies for drones.
* **Risk**: High rate of false positives on general aerial scenes with birds, clouds, or flying debris.
* **Remediation**: Fine-tune YOLOv8-Nano specifically on drone and landing-pad datasets.

### 2.2 Optical Flow & Motion Analysis
* **Issue**: `cv2.calcOpticalFlowFarneback` computes dense flow across the entire frame on CPU at $1280 \times 720$.
* **Risk**: High latency and severe CPU utilization spikes.
* **Remediation**: Migrate to Sparse Lucas-Kanade optical flow (`cv2.calcOpticalFlowPyrLK`) focused on feature points inside regions of interest (ROI).

### 2.3 Pose Estimation & Metric Geometry
* **Issue**: The current code has **zero metric 3D pose estimation**. The camera intrinsic matrix $K$, lens distortion parameters $D$, and physical landing pad dimensions are completely absent.
* **Remediation**: Implement a dedicated `CalibrationManager` and `PoseEstimator` utilizing `cv2.solvePnP` with planar targets.
