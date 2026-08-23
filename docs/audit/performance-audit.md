# SkyVanta AI — Performance & Telemetry Benchmarking Audit (V0)

## 1. Performance Measurement Audit

> [!NOTE]
> Per Rule #2, unmeasured parameters are strictly classified as **NOT CURRENTLY MEASURED** or **PLANNED TARGET**. No fabricated or assumed performance figures are documented.

| Performance Metric | Code Location / Measurement Mechanism | Current Value / Status | Classification |
| :--- | :--- | :--- | :--- |
| **Pipeline Processing FPS** | `main.py:1020-1021` (`real_fps = (frame_idx + 1) / elapsed`) | Dynamically calculated per video run | **MEASURED RUNTIME METRIC** |
| **HUD Render Smooth FPS** | `main.py:807` (`_fps_smooth = lerp(_fps_smooth, fps, 0.1)`) | Filtered display metric on HUD overlay | **VISUALIZATION ONLY** |
| **YOLO Inference Latency** | *Zero latency profiling code around `model.predict()`.* | **NOT CURRENTLY MEASURED** | Planned Target: $\le 15\text{ ms}$ |
| **Motion Detector Latency**| *Zero profiling around `calcOpticalFlowFarneback`.* | **NOT CURRENTLY MEASURED** | Planned Target: $\le 5\text{ ms}$ |
| **End-to-End Latency** | *No glass-to-actuator timestamp tracking.* | **NOT CURRENTLY MEASURED** | Planned Target: $\le 45\text{ ms}$ |
| **CPU Utilization (%)** | *No `psutil` or OS performance counters.* | **NOT CURRENTLY MEASURED** | Unmeasured |
| **GPU Utilization (%)** | *No `pynvml` or CUDA event timers.* | **NOT CURRENTLY MEASURED** | Unmeasured |
| **Memory RSS Footprint** | *No memory tracking or leak profiling.* | **NOT CURRENTLY MEASURED** | Unmeasured |
| **Frame Drop Rate** | *No frame drop detection logic in video loop.* | **NOT CURRENTLY MEASURED** | Unmeasured |

---

## 2. Profiling Infrastructure Recommendations (Volume 15)
1. **Instrument Microsecond Timers**: Add a non-blocking `LatencyProfiler` measuring discrete stage durations:
   $$\Delta t_{total} = \Delta t_{preprocess} + \Delta t_{yolo} + \Delta t_{motion} + \Delta t_{tracking} + \Delta t_{hud}$$
2. **CUDA Event Timing**: Replace wall-clock `time.time()` with `torch.cuda.Event(enable_timing=True)` to accurately profile GPU execution without CPU-GPU synchronization stalls.
