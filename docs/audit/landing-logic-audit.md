# SkyVanta AI — Landing Logic & Telemetry Audit (V0)

## 1. Classification of Current Telemetry & Landing Parameters

> [!IMPORTANT]
> The table below audits every telemetry and landing metric currently generated in `main.py` (`TelemetryEstimator` and `ApproachCorridor`) to explicitly differentiate between **physical measurements**, **state estimations**, **heuristics**, and **visualization-only graphics**.

| Parameter | Mathematical Formulation in Code | Classification | Source Code Line | Physical Validity & Reliability |
| :--- | :--- | :--- | :--- | :--- |
| **Distance** | `clamp(ref_diag / max(diag, 1e-3) * 8.0, 3.0, 120.0)` | **HEURISTIC** | `main.py:467` | **Zero physical validity**. Approximates distance purely from bounding box pixel size relative to screen diagonal. |
| **Altitude** | `2.0 + norm_y * 40.0 + scale_trend * 3.0` | **HEURISTIC** | `main.py:471` | **Zero physical validity**. Assumes altitude correlates directly with vertical pixel position on the image plane. |
| **Approach Angle** | `clamp(norm_x_off * 12.0, -25.0, 25.0)` | **HEURISTIC** | `main.py:475` | **Zero physical validity**. Scales horizontal pixel offset by a constant factor of 12.0 degrees. |
| **Alignment Score** | `clamp(100.0 - abs(norm_x_off)*60.0 - abs(angle)*0.8, 30.0, 99.0)` | **HEURISTIC** | `main.py:478` | **Synthetic score**. Inversely penalizes lateral image offset. Does not represent true geometric alignment. |
| **Lateral Offset** | `norm_x_off * 3.2` | **HEURISTIC** | `main.py:481` | **Synthetic metric**. Multiplies normalized $x$ coordinate by 3.2m arbitrarily. |
| **Vertical Offset** | `clamp(norm_y_off * 2.5, -4.0, 4.0)` | **HEURISTIC** | `main.py:485` | **Synthetic metric**. Multiplies normalized $y$ coordinate by 2.5m arbitrarily. |
| **Landing Confidence**| `clamp(track_conf * 100.0 * (0.6 + 0.4 * (1 - abs(norm_x_off))), 0, 99)` | **HEURISTIC** | `main.py:488` | **Synthetic heuristic**. Blends detection confidence with screen center proximity. |
| **Landing Zone Base**| `zone_y = lerp(h * 0.72, h * 0.90, closeness)` | **VISUALIZATION ONLY** | `main.py:527` | **Pure graphical overlay**. Places a quadrilateral at the bottom of the screen to simulate a landing area. |
| **Approach Corridor**| Trapezoid connecting drone center $(cx, cy)$ to landing zone | **VISUALIZATION ONLY** | `main.py:534` | **Pure graphical overlay**. Renders animated dashed lines and shaded polygons between drone and virtual zone. |
| **Approach Radar** | 2D circular radar widget with sweeping line and historical dots | **VISUALIZATION ONLY** | `main.py:884` | **Pure graphical HUD widget**. Projects relative 2D pixel coordinates onto a radar reticle. |
| **Landing State** | `SEARCHING`, `ACQUIRED`, `TRACKING`, `LOCKED`, `APPROACHING` | **HEURISTIC FSM** | `main.py:410` | Driven entirely by detection confidence thresholds and hit counts; **no connection to flight control or vehicle physics**. |

---

## 2. Critical Architectural Conclusions
1. **The current repository contains NO real landing guidance algorithms.** It contains visual telemetry heuristics crafted for video overlay presentation.
2. **Zero Closed-Loop Control**: There is no descent velocity profiling, glide-slope planning, waypoint generation, or PID/LQR controller.
3. **Transition to Metric State Estimation**: In Volume 5 and Volume 6, `TelemetryEstimator` must be replaced with the **Error-State Extended Kalman Filter (ESEKF)**, which derives true metric distance, altitude, and velocities from calibrated camera PnP pose, 1D LiDAR rangefinders, and 6-DoF IMU measurements.
