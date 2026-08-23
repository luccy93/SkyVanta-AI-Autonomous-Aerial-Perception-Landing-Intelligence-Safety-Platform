# SkyVanta AI — Volume 1 Migration Guide

---

## 1. Migration Overview

Volume 1 refactors the monolithic single-file prototype (`main.py`) into the modular `skyvanta` Python package while preserving complete backward compatibility and identical algorithmic behavior.

---

## 2. Component Mapping Table

| Monolithic `main.py` Component | Modular `skyvanta` Package Component | Key Improvements & Changes |
| :--- | :--- | :--- |
| Dynamic `_ensure()` pip calls (L9–L33) | `pyproject.toml` / `requirements.txt` | Removed runtime environment mutation; declarative dependencies. |
| `Palette` class (L52–L65) | `skyvanta.visualization.palette.Palette` | Type-annotated OpenCV BGR color constants. |
| Math helpers: `clamp`, `lerp`, `lerp_pt`, `ease` (L69–L84) | Module-level helpers in tracking & visualization | Typed functions with explicit range guards. |
| `OneEuroFilter`, `Vec2EuroFilter` (L85–L137) | `skyvanta.tracking.smoothing` | Isolated, tested, added `reset()` lifecycle method. |
| `KalmanBox2D` (L138–L172) | `skyvanta.tracking.kalman.KalmanBox2D` | Fixed 2D column matrix dimensions `(8, 1)` and `(4, 1)` for OpenCV 4/5 compatibility; configurable noise. |
| `YoloDroneDetector` (L174–L208) | `skyvanta.perception.detector.YoloDroneDetector` | Decoupled configuration, graceful fallback on missing package, typed `Detection` objects. |
| `MotionContrastDetector` (L210–L276) | `skyvanta.perception.motion.MotionContrastDetector` | Configurable history, variance, and area thresholds; returns typed `Detection` list. |
| Candidate selection `_pick_best()` (L305–L331) | `skyvanta.perception.fusion.CandidateFusion` | Standalone fusion class with configurable IoU threshold. |
| `DroneTracker` (L278–L445) | `skyvanta.tracking.tracker.DroneTracker` | Modularized; state machine separated into `TrackStateMachine`; returns typed `TrackInfo`. |
| `TelemetryEstimator` (L447–L501) | `skyvanta.telemetry.estimator.TelemetryEstimator` | Explicit heuristic terminology (`estimated_distance_m`, `estimated_altitude_m`, etc.); returns `TelemetryEstimate`. |
| `ApproachCorridor` (L503–L553) | `skyvanta.visualization.corridor.ApproachCorridor` | Returns typed `ApproachCorridorGeometry` data model. |
| Drawing helpers (L555–L628) | `skyvanta.visualization.drawing` | Comprehensive primitive library (`draw_dashed_line`, `draw_glow_circle`, `rounded_rect`, `frame_corners`, `scanline`). |
| `HUDRenderer` (L630–L931) | `skyvanta.visualization.hud.HUDRenderer` | Compositor decoupled from tracker internals; accepts typed snapshots. |
| Procedural demo generator (L1043–L1261) | `skyvanta.simulation.synthetic` | Generator class `SyntheticSceneGenerator` allowing deterministic, parameterized synthetic testing. |
| Video processing loop `process_video()` (L951–L1040) | `skyvanta.pipeline.runner.PipelineRunner` | Orchestrator class with clean frame-by-frame pipeline and structured logging. |
| CLI execution `main()` (L1262–L1286) | `skyvanta.cli` and `skyvanta.__main__` | Standardized CLI flags (`-i`, `-o`, `-c`, `--demo`, `--yolo`, `--no-yolo`). |
| Standalone `main.cpp` (175 lines) | `cpp/src/main.cpp` + `cpp/CMakeLists.txt` | Standardized CMake build structure under `cpp/`. |

---

## 3. Preserved Legacy Compatibility

The original prototype files remain fully accessible and functional under `legacy/`:
* `legacy/main.py`: Executable via `python legacy/main.py [video.mp4]`
* `legacy/main.cpp`: Build instructions preserved in `legacy/README.md`

All mathematical formulas, filter coefficients, and HUD styling from the legacy prototype are preserved with 100% numerical parity verified by `tests/characterization/test_legacy_parity.py`.
