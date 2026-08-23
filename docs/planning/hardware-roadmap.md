# SkyVanta AI — Hardware Roadmap & Tiered Architecture

## 1. Hardware Selection Philosophy
SkyVanta AI avoids premature capital expenditure and hardware lock-in by defining **three distinct hardware development tiers**. Development begins strictly on Level A (Simulation & Software-only), transitioning to Level B and Level C only as software validation milestones are systematically passed.

```
+-----------------------------------------------------------------------------------+
| LEVEL A: Software-Only & Simulation Rig (Zero Hardware Purchase Required)          |
| -> Host PC (x86_64 / RTX GPU), Gazebo Harmonic, PX4 SITL, WebRTC GCS Dashboard     |
+-----------------------------------------------------------------------------------+
                                         |
                                         v (After passing V0-V9 Simulation Gates)
+-----------------------------------------------------------------------------------+
| LEVEL B: Low-Cost Bench & Airframe Prototype (~$600 - $900 Total Budget)          |
| -> Raspberry Pi 5 / Jetson Nano 4GB, Pixhawk 4 / 6C, Pi Camera v3, Benewake TFmini |
+-----------------------------------------------------------------------------------+
                                         |
                                         v (After passing V10-V16 HIL & Tethered Gates)
+-----------------------------------------------------------------------------------+
| LEVEL C: Production-Grade Edge & Advanced Airframe (~$2,500 - $4,500 Budget)      |
| -> NVIDIA Jetson Orin Nano / NX, Cube Orange+, Global Shutter Stereo, Lightware 1D|
+-----------------------------------------------------------------------------------+
```

---

## 2. Hardware Tier Specifications

| Component Subsystem | LEVEL A: Software-Only Sim | LEVEL B: Low-Cost Prototype | LEVEL C: Advanced Edge Rig |
| :--- | :--- | :--- | :--- |
| **Compute Platform** | Host PC (Intel i7/Ryzen 7, RTX 3060/4070, 32GB RAM, Ubuntu 22.04) | **Raspberry Pi 5 (8GB)** or **NVIDIA Jetson Nano 4GB** | **NVIDIA Jetson Orin Nano (8GB)** or **Jetson Orin NX (16GB)** |
| **Flight Controller** | PX4 Autopilot SITL (v1.14+) / ArduPilot SITL running natively | **Pixhawk 6C** or **Holybro Pixhawk 4** (running PX4 1.14) | **Cube Orange+** (Triple Redundant IMU, isolated dampening) |
| **Primary Vision Sensor** | Gazebo Virtual RGB Camera plugin ($1280 \times 720$ @ 30 FPS) | **Raspberry Pi Camera Module 3** (Sony IMX708, Autofocus, CSI) | **Sony IMX296 Global Shutter CSI Camera** or **Intel RealSense D435i / OAK-D Pro** |
| **Altimeter / Rangefinder** | Simulated 1D Gazebo Ray Sensor (10 Hz, 0.01m noise) | **Benewake TFmini-S Micro LiDAR** (Range: 0.1–12m, UART / I2C) | **Lightware SF11/C Laser Altimeter** (Range: 0.1–100m, 50 Hz, IP67) |
| **Inertial Measurement** | Simulated 6-DoF Gazebo IMU plugin (100 Hz, thermal drift model) | Onboard InvenSense ICM-42688-P (via Pixhawk internal IMU) | Dual internal isolated IMUs + External VectorNav VN-100 (Optional) |
| **Telemetry Link** | Localhost UDP (`127.0.0.1:14550`) / WebSockets | **ESP32 Wi-Fi Bridge** or **SiK 915MHz Radio Telemetry V3 (500mW)** | **Holybro Microhard P900 Radio (900MHz, 1W)** or **4G/LTE Companion Dongle** |
| **Landing Target Base** | Virtual 3D Gazebo model with nested AprilTag 36h11 + 'H' pad | Printed high-contrast matte PVC vinyl pad ($60 \times 60\text{ cm}$) | Active LED-illuminated weather-sealed landing pad with IR beacon |
| **Airframe / Test Rig** | Simulated Holybro X500 V2 quadrotor model | **F450 Quadcopter Kit** or **Holybro S500 V2** frame | **Holybro X500 V2 Carbon Fiber Frame** (with quick-release payload bay) |
| **Power Delivery** | N/A (Software) | 4S 5000mAh LiPo + 5V/5A BEC for Companion Computer | 6S 6000mAh LiPo + Dedicated Mauch Precision Power Hub & Regulators |

---

## 3. Procurement & Safety Rules
1. **Zero Hardware Purchases During Planning**: No components shall be ordered before complete review and approval of the `PROJECT_MASTER_PLAN.md`.
2. **Simulation-First Gating**: No physical airframe shall be powered or integrated until all 18 canonical simulation scenarios pass with 100% automated regression in Level A.
3. **Bench Isolation**: Level B and Level C initial testing must occur on an indoor static bench with propellers removed and motor outputs disabled.
