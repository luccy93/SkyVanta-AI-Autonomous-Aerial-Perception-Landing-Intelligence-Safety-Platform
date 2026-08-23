# SkyVanta AI — Repository Cleanup & Refactoring Plan (V0)

## 1. Inventory of Files & Technical Debt

> [!NOTE]
> Per the V0 Planning and Audit rules, **no files are deleted or modified during this phase**. This document catalogs items recommended for refactoring, relocation, or cleanup in Volume 1.

```
+---------------------------------------------------------------------------------------------------+
|                                  FILE INVENTORY & REFACTORING PLAN                                |
+---------------------------------------------------------------------------------------------------+
```

| File / Artifact | Current Purpose & Contents | Identified Issue / Technical Debt | Recommended Action in Volume 1 |
| :--- | :--- | :--- | :--- |
| **`main.py`** | 1,286-line monolithic Python script containing everything from PIP installation to HUD rendering. | Violates Single Responsibility Principle. Difficult to test or maintain. | **REFACTOR & MODULARIZE**: Split into `skyvanta.perception`, `skyvanta.tracking`, `skyvanta.geometry`, `skyvanta.hud`. |
| **`main.cpp`** | 175-line standalone bouncing ball Kalman filter demo. | Not connected to the Python pipeline or any camera input; dead demo code. | **PRESERVE & MIGRATE**: Move HUD drawing utilities into `cpp/hud_utils/` for future C++ edge visualization. |
| **`_ensure()`** function in `main.py` | Dynamic runtime `pip install` subprocess calls. | Unsafe, non-deterministic, causes random runtime crashes if offline. | **REMOVE IN V1**: Replace with static `pyproject.toml` and locked dependencies. |
| **`output/`** directory | Generated video files (`demo_perception.mp4`, etc.). | Output artifacts should not be committed to Git. | **ADD TO `.gitignore`**: Ensure test outputs are stored in ignored scratch directories. |
| **Missing `requirements.txt`** | Stated in `README.md` but missing from filesystem. | Causes setup confusion for new developers. | **CREATE IN V1**: Add standard `requirements.txt` and `pyproject.toml`. |
| **Missing `CMakeLists.txt`** | C++ build commands currently documented only as header comments. | No standardized build system for C++ components. | **CREATE IN V1**: Add modern CMake configuration supporting C++20 and OpenCV 4.8+. |
