# SkyVanta AI — Dependency & Package Audit (V0)

## 1. Package Inventory & Classification

```
+---------------------------------------------------------------------------------------------------+
|                                 DEPENDENCY CLASSIFICATION MATRIX                                  |
+---------------------------------------------------------------------------------------------------+
```

| Package / Library | How Imported / Invoked | Classification | Risk Level | Evaluation & Recommendations |
| :--- | :--- | :--- | :---: | :--- |
| **`numpy`** | `import numpy as np` (via `_ensure`) | **CORE** | Low | Essential for vector math, image arrays, and matrix operations. |
| **`opencv-contrib-python`**| `import cv2` (via `_ensure`) | **CORE** | Low | Core computer vision, MOG2 background subtraction, Farneback optical flow, Kalman filter, and HUD rendering. |
| **`scipy`** | `from scipy.optimize import linear_sum_assignment` | **CORE** | Low | Hungarian assignment matcher (imported conditionally; used for future tracking). |
| **`ultralytics`** | `from ultralytics import YOLO` (via `_ensure`) | **CORE / OPTIONAL** | Medium | Provides YOLOv8 inference. Note: Auto-downloads `yolov8n.pt` from internet at runtime if missing. |
| **`requirements.txt`** | *Referenced in README.md, but missing on disk.* | **MISSING** | High | Project has no locked dependencies file on disk. |
| **`c_library_v2` / `pymavlink`**| *Not imported or installed.* | **FUTURE-PLANNED** | Low | Required in Volume 10 for MAVLink 2.0 communication. |
| **`pupil-apriltags` / `opencv-contrib` ArUco**| *Not imported or installed.* | **FUTURE-PLANNED** | Low | Required in Volume 4 for Level 1 fiducial pose estimation. |
| **`eigen3`** (C++) | *Not installed or configured.* | **FUTURE-PLANNED** | Low | Required in Volume 6 for C++ 15-State Error EKF matrix calculations. |
| **`fastapi` / `websockets`**| *Not imported or installed.* | **FUTURE-PLANNED** | Low | Required in Volume 11 for GCS telemetry streaming gateway. |

---

## 2. Technical Debt & Risks in Dependency Management

### 2.1 Dynamic Runtime Package Installation (`_ensure()`)
* **Current Behavior**: `main.py` lines 9–33 execute `subprocess.check_call([sys.executable, "-m", "pip", "install", ...])` during script execution if a package is not found.
* **Architectural Risk**:
  1. Non-deterministic execution: If internet connectivity drops, the script crashes.
  2. Potential environment corruption in restricted/sandboxed operating systems.
  3. Slow startup times.
* **Remediation for Volume 1**: Remove dynamic `_ensure()` pip calls. Manage dependencies deterministically via a locked `pyproject.toml` and standard `requirements.txt` / virtual environment.
