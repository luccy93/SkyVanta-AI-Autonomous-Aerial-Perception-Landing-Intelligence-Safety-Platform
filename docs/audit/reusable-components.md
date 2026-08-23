# SkyVanta AI — Reusable Component Mapping (V0)

## 1. Component Reusability Matrix

```
+---------------------------------------------------------------------------------------------------+
|                                  REUSABLE COMPONENT CLASSIFICATION                                |
+---------------------------------------------------------------------------------------------------+
```

| Component Name | Source Location | Classification | Future Role in SkyVanta Architecture | Refactoring Guidance |
| :--- | :--- | :---: | :--- | :--- |
| **`OneEuroFilter` & `Vec2EuroFilter`** | `main.py:85-137` | **KEEP** | Standard 1D & 2D jitter reduction filter for UI reticles and telemetry smoothing. | Move to `skyvanta.common.filters.one_euro`. Add docstrings and unit tests. |
| **`MotionContrastDetector`** | `main.py:210-276` | **REFACTOR** | Fallback motion perception layer for non-semantic visual cues. | Replace whole-frame Farneback with Sparse LK to reduce CPU utilization. Move to `skyvanta.perception.motion`. |
| **`KalmanBox2D`** | `main.py:138-171` | **WRAP WITH INTERFACE** | 2D bounding box tracking filter in image pixel space. | Wrap inside standard `BaseTracker` interface. Move to `skyvanta.tracking.kalman_2d`. |
| **`HUDRenderer`** | `main.py:630-931` | **WRAP WITH INTERFACE** | Generates rich visual HUD overlays for real-time video streaming to GCS. | Move to `skyvanta.visualization.hud`. Decouple from pipeline logic. |
| **`_synth_background()` & `_zoom_pan()`** | `main.py:1043-1211` | **KEEP** | Procedural scene generator for offline computer vision test harnesses. | Move to `skyvanta.simulation.synthetic_scene`. |
| **`hud::` drawing utilities** | `main.cpp:11-114` | **KEEP** | Fast OpenCV C++ rendering functions (glow circles, dashed lines, rounded rects). | Move to `cpp/include/skyvanta/hud_drawing.hpp`. |
| **`YoloDroneDetector`** | `main.py:174-208` | **REPLACE LATER** | Primary deep learning detector. | Replace standard COCO proxy classes with custom fine-tuned YOLOv8-Nano pad/airframe model. |
| **`TelemetryEstimator`** | `main.py:447-500` | **REPLACE LATER** | Visual telemetry approximations. | Replace with **15-State Error-State EKF** and PnP 6-DoF metric pose solver. |
| **`ApproachCorridor`** | `main.py:503-552` | **REFACTOR** | Visual 3D trapezoidal approach corridor. | Retain rendering logic, but drive corridor vertices with true 3D metric camera-to-pad PnP coordinates. |
| **`DroneTracker._pick_best()`** | `main.py:305-332` | **REPLACE LATER** | Single-target greedy IoU detection matcher. | Replace with **Hungarian Assignment Matcher** supporting multi-target tracking. |
