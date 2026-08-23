# SkyVanta AI — Current Repository Architecture (V0 Audit)

## 1. System Summary & Scope of Current Implementation
The current repository is a **monolithic Python & C++ visual perception prototype** designed to process prerecorded drone video files or generate a synthetic demonstration video.

It implements 2D object detection, motion segmentation, 2D Kalman box filtering, One Euro smoothing, heuristic 2D visual telemetry approximations, and a high-framerate OpenCV HUD rendering engine.

```
+---------------------------------------------------------------------------------------------------+
|                                  CURRENT REPOSITORY RUNTIME ARCHITECTURE                          |
+---------------------------------------------------------------------------------------------------+

                    [ Input Video (MP4) ]  OR  [ Synthetic Procedural Scene Generator ]
                                      |
                                      v
                             [ Frame Preprocessing ]
                           (Letterbox / Scale to <=1280px)
                                      |
               +----------------------+----------------------+
               |                                             |
               v                                             v
     [ YoloDroneDetector ]                       [ MotionContrastDetector ]
  (YOLOv8n: bird/kite/airplane)               (MOG2 BG Sub + Farneback Flow + Canny)
               |                                             |
               +----------------------+----------------------+
                                      |
                                      v
                            [ _pick_best() Fusion ]
                          (IoU overlap & Area Scoring)
                                      |
                                      v
                             [ DroneTracker Core ]
               +----------------------+----------------------+
               |                                             |
               v                                             v
        [ KalmanBox2D ]                              [ Vec2EuroFilter ]
   (cv2.KalmanFilter 8x4)                        (Adaptive Cutoff Filtering)
               |                                             |
               +----------------------+----------------------+
                                      |
                                      v
                        [ 5-State Tracking FSM ]
              (SEARCHING -> ACQUIRED -> TRACKING -> LOCKED -> APPROACHING)
                                      |
               +----------------------+----------------------+
               |                                             |
               v                                             v
     [ TelemetryEstimator ]                        [ ApproachCorridor ]
   (Heuristic Visual Math)                       (Trapezoidal Perspective Mesh)
               |                                             |
               +----------------------+----------------------+
                                      |
                                      v
                             [ HUDRenderer Engine ]
            (OpenCV BGR Overlay, Glow Circles, Radar Widget, Scantracks)
                                      |
                                      v
                         [ VideoWriter Output (MP4) ]
```

---

## 2. Component Pipeline Analysis

### 2.1 Video Ingestion & Sizing
* **Source**: `process_video()` in `main.py`.
* **Mechanism**: Reads frames via `cv2.VideoCapture`. If video dimensions exceed 1280px, frames are scaled down while preserving aspect ratio.
* **Fallback / Demo**: `run_demo()` procedurally creates synthetic sky, rolling hill grounds, roads, and animated drone movement via Gaussian noise random walks.

### 2.2 Dual Detection Layer
1. **`YoloDroneDetector`**:
   * Uses pretrained `yolov8n.pt` from Ultralytics.
   * Filters for proxy classes: `airplane`, `bird`, `kite`, `frisbee` at confidence $\ge 0.08$.
   * Does not have a dedicated drone or landing-pad trained weight file.
2. **`MotionContrastDetector`**:
   * Combines `cv2.createBackgroundSubtractorMOG2`, `cv2.calcOpticalFlowFarneback`, and `cv2.Canny` edge density.
   * Generates candidate bounding boxes ranked by edge density and area.

### 2.3 Association & Tracking
* **`DroneTracker`**:
   * Associates detections via 2D IoU overlap (`_pick_best`).
   * Updates `KalmanBox2D` (8-state constant velocity model on bounding box $cx, cy, w, h$).
   * Applies `Vec2EuroFilter` on center position and `OneEuroFilter` on size.
   * State transitions based on confidence thresholds and hit/miss frame counters.

### 2.4 Visual Telemetry Estimation (Heuristic)
* **`TelemetryEstimator`**:
   * *Distance*: Inversely proportional to bounding box diagonal: `ref_diag / diag * 8.0`.
   * *Altitude*: Inferred from vertical pixel height: `2.0 + norm_y * 40.0 + scale_trend * 3.0`.
   * *Angle / Alignment / Offsets*: Inferred from normalized $x/y$ pixel deviation from screen center.
   * *Note*: **None of these values are metric physical measurements.** They are visual heuristics designed for HUD aesthetics.

### 2.5 HUD & Video Output
* **`HUDRenderer`**:
   * Composites multi-layered BGR graphics: 3D perspective approach corridor, dashed lines, glowing lock reticles, approach radar mini-map, telemetry data tables, scanlines, and vignette borders.
   * Writes rendered frames to `output/{name}_perception.mp4` via `cv2.VideoWriter`.

---

## 3. Standalone C++ Component (`main.cpp`)
* Implements a standalone bouncing ball simulation with a 4-state `cv::KalmanFilter` in `main.cpp`.
* Contains reusable C++ HUD drawing functions in namespace `hud::`.
* Is not connected to `main.py`, does not ingest camera frames, and does not interface with robotics hardware.
