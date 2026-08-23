# SkyVanta AI — Technical Risk Register & Validation Matrix (V0)

## 1. Technical Risk Evaluation & Gating Matrix

```
Severity (1: Low, 5: Critical/Catastrophic) | Likelihood (1: Rare, 5: Almost Certain)
RPN (Risk Priority Number = Severity x Likelihood)
```

| Risk ID | Technical Risk Description | Sev | Lkh | RPN | Mitigation Strategy | Planned Validation Method |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **TR-01** | **False Positive Target Detection**: Clutter or shadows detected as landing pad. | 4 | 3 | 12 | Require multi-stage Level 1 (AprilTag ID) or Level 2 geometric symmetry gate before accepting track. | Scenario SC-12: Injected distractor pads in Gazebo SITL simulation. |
| **TR-02** | **False Negative / Detection Dropout**: Target lost during sudden illumination change or glare. | 4 | 4 | 16 | Apply CLAHE contrast enhancement; propagate target state via ESEKF dead-reckoning. | Scenario SC-03: Solar glare injection test in Gazebo SITL. |
| **TR-03** | **Rapid Ego-Motion Blur**: Wind gusts induce camera motion blur, corrupting feature tracking. | 4 | 3 | 12 | Use high-shutter camera settings ($< 1/500\text{s}$); fuse high-rate IMU angular rates in ESEKF. | Scenario SC-08: Wind shear and lateral gust injection test. |
| **TR-04** | **Monocular Scale Ambiguity**: Inaccurate altitude or distance estimation from single camera. | 5 | 3 | 15 | Fuse 1D LiDAR laser altimeter directly in ESEKF measurement update. | Scenario SC-10: LiDAR sensor comparison against visual PnP height. |
| **TR-05** | **Incorrect PnP Pose Solution**: Ambiguous planar homography causing inverted or tilted pose. | 5 | 2 | 10 | Use `SOLVEPNP_IPPE` (Infinitesimal Plane-based Pose Estimation) specifically engineered for planar fiducials. | Automated unit tests comparing PnP output against known 3D ground truth. |
| **TR-06** | **Pipeline Latency Spikes**: Frame processing exceeding 50ms, causing feedback control instability. | 4 | 3 | 12 | TensorRT INT8 execution; asynchronous threading separating perception from 100 Hz ESEKF. | End-to-end latency profiling with microsecond hardware timers in Volume 15. |
| **TR-07** | **Sensor Failure / Loss**: LiDAR or IMU disconnects or reports NaN during terminal descent. | 5 | 2 | 10 | Sensor health watchdogs; automatic rejection of divergent sensors; fallback to barometric height. | Scenario SC-10: Runtime sensor fault injection in SITL. |
| **TR-08** | **Premature / Unsafe Touchdown**: Commanded descent when vehicle is misaligned with pad. | 5 | 2 | 10 | Deterministic safety supervisor enforces hard invariant gate: lateral error $< 5\text{cm}$, tilt $< 3^\circ$. | Scenario SC-09: Alignment gate violation abort test in SITL. |
| **TR-09** | **MAVLink Disconnect / Jitter**: Serial UART communication failure between companion and autopilot. | 5 | 2 | 10 | Hardware heartbeat watchdog on Pixhawk; automatic fallback to internal Autopilot RTL. | Scenario SC-14 & SC-17: Serial cable disconnect test in SITL/HIL. |
| **TR-10** | **Process Memory Corruption**: C++ memory leak or segmentation fault during flight. | 4 | 2 | 8 | Zero-allocation real-time loops in C++; AddressSanitizer (ASan) and Valgrind in CI/CD pipeline. | Automated 1-hour stress test harness in CI/CD. |
