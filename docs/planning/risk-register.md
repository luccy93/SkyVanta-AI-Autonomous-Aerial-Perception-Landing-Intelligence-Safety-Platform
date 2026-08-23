# SkyVanta AI — Risk Register & Mitigation Strategy

## 1. Risk Evaluation Matrix
Risks are evaluated according to **Severity** (1–5), **Likelihood** (1–5), and resulting **Risk Priority Number (RPN = Severity $\times$ Likelihood)**.

```
Severity (1: Negligible, 2: Minor, 3: Moderate, 4: Critical, 5: Catastrophic)
Likelihood (1: Rare, 2: Unlikely, 3: Moderate, 4: Likely, 5: Almost Certain)
```

---

## 2. Comprehensive Risk Register

| Risk ID | Risk Description | Sev | Lkh | RPN | Mitigation Strategy | Early Detection Mechanism | Recovery & Fail-Safe Action |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| **RSK-01** | **Visual Detector False Positive**: AI locks onto ground clutter/shadows instead of landing pad. | 4 | 3 | 12 | Require multi-stage verification: Level 1 fiducial ID or Level 2 geometric circular symmetry check before accepting detection. | Low temporal confidence score; inconsistent bounding box scale; geometric aspect ratio mismatch. | Invalidate detection, revert state to `SEARCHING`, hold current altitude. |
| **RSK-02** | **Motion Blur Track Loss**: Sudden wind gust causes rapid camera movement and visual track loss. | 4 | 4 | 16 | Use high shutter speed camera settings ($< 1/500\text{s}$), ESEKF IMU dead-reckoning during brief frame drops. | Optical flow velocity spike; detection missing for $> 1$ frame. | Kalman filter propagates state for up to 1.0s; if unrecovered, trigger `HOLD`. |
| **RSK-03** | **Altimeter Scale Ambiguity**: Monocular vision scale errors causing inaccurate height estimation. | 5 | 3 | 15 | Mandatory hardware 1D LiDAR rangefinder (Benewake/Lightware) fused directly in ESEKF state vector. | Discrepancy between visual PnP $z$ and LiDAR rangefinder $> 0.4\text{m}$. | Discard vision height estimate; constrain altitude strictly using LiDAR/barometer. |
| **RSK-04** | **Edge Compute Thermal Throttling**: Jetson/Pi CPU/GPU throttles due to heat in field test, dropping FPS. | 4 | 3 | 12 | Optimize neural network using TensorRT INT8; implement active PWM cooling fan; benchmark in thermal chamber. | Onboard thermal daemon monitoring SoC temperatures $> 75^\circ\text{C}$; FPS drop below 20. | Safety supervisor restricts maximum drone descent velocity to match lower perception update rate. |
| **RSK-05** | **MAVLink Serial Disconnect**: UART cable vibration disconnects companion computer from Pixhawk. | 5 | 2 | 10 | Locking JST-GH connectors with vibration strain relief; hardware hardware watchdog on Pixhawk. | Pixhawk MAVLink heartbeat timeout $> 500\text{ms}$. | Pixhawk autonomously engages internal failsafe (RTL or Auto-Land at current spot). |
| **RSK-06** | **Adverse Ground Ground-Effect (Rotor Wash)**: Severe air turbulence and dust kicking up near ground ($< 0.5\text{m}$). | 4 | 4 | 16 | Execute rapid, decisive final touchdown sequence once aligned within 0.3m; do not loiter in ground effect. | Sudden IMU vertical acceleration fluctuations and optical flow divergence below 0.5m. | Final commitment command: trigger motor disarm immediately upon touch detection. |
| **RSK-07** | **Dynamic Moving Pad Acceleration**: Target boat/vehicle changes velocity or turns during final descent. | 4 | 3 | 12 | ESEKF actively estimates target velocity ($\vec{v}_{pad}$) and acceleration ($\vec{a}_{pad}$); abort if acceleration exceeds limits. | Target relative velocity derivative exceeds $1.2\text{ m/s}^2$. | FSM transitions to `HOLD` or `ABORT` climb if landing envelope is exceeded. |
| **RSK-08** | **Software Memory Leak / Crash**: C++ memory corruption or Python memory leak during long mission. | 4 | 2 | 8 | Zero-allocation real-time loops in C++; AddressSanitizer (ASan) and Valgrind in CI/CD pipeline. | Watchdog process monitoring memory RSS usage; IPC heartbeat checks. | Isolated process architecture: perception crash does not kill safety supervisor or MAVLink link. |
| **RSK-09** | **GPS Jamming / Degradation**: Operation in degraded GPS urban canyons. | 3 | 4 | 12 | Entire landing stack is engineered for pure vision + IMU + rangefinder localization; zero reliance on global GPS during approach. | GPS HDOP $> 2.5$ or satellite count $< 6$. | Autopilot switches from GPS Navigation mode to Vision-Guided Offboard mode. |
| **RSK-10** | **Safety Pilot Latency / Inattention**: Human pilot fails to react in time during an unpredicted physical test anomaly. | 5 | 2 | 10 | Independent automated safety supervisor handles sub-50ms aborts; safety pilot is redundant secondary safeguard. | Automated boundary invariant check violation. | Automated immediate climb to safe altitude ($15\text{m}$) without waiting for human intervention. |
