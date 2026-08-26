# SkyVanta AI — Autonomous Aerial Perception, Landing Intelligence & Safety Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI Status](https://github.com/luccy93/SkyVanta-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/luccy93/SkyVanta-AI/actions/workflows/ci.yml)
[![Tests Passing](https://img.shields.io/badge/tests-251%20passed-brightgreen.svg)](tests/)

**Developer / Creator:** SkyVanta-AI / Devendraprasad  
**Repository:** [https://github.com/luccy93/SkyVanta-AI](https://github.com/luccy93/SkyVanta-AI)

---

## 1. System Overview

**SkyVanta AI (Volumes V1–V9)** is a modular, deterministic, simulation-first computer vision, 15-state sensor fusion, and autonomous landing intelligence platform. It provides end-to-end aerial target perception, 6-DoF fiducial pose estimation, SE(3) spatial frame graph transformation, Error-State Extended Kalman Filter (ESEKF) inertial fusion, 12-state hierarchical landing supervision, and closed-loop digital twin scenario validation.

### Core Architectural Capabilities:
* **Multi-Cue Perception Pipeline (V2)**: Multi-cue candidate fusion combining YOLO deep learning inference (with strict offline weight checking) with MOG2 background subtraction, Farneback dense optical flow, and Canny edge scoring.
* **Multi-Target Tracking & Smoothing (V3)**: Track lifecycle manager with 2D Kalman box filtering and dual One-Euro adaptive low-pass filters for zero-latency jitter reduction.
* **6-DoF Landing Pad Pose Estimation (V4)**: Monocular ArUco / AprilTag fiducial detection with OpenCV IPPE / ITERATIVE Perspective-n-Point (PnP) solvers and pose quality rating.
* **Spatial Coordinate Frame Graph (V5)**: $\text{SE}(3)$ Lie group transformation engine with Breadth-First Search frame traversal across `CAMERA`, `BODY`, `LANDING_PAD`, and `WORLD` (ENU).
* **15-State ESEKF Sensor Fusion (V6)**: Multi-rate 100Hz IMU propagation and 30Hz visual pose measurement injection with Chi-squared innovation gating and SO(3) error state injection.
* **Landing Intelligence & Safety Supervisor (V7)**: 12-state operational Finite State Machine (FSM) enforcing hard safety invariants (e.g. irrevocable abort-climb invariants upon sensor dropout or excessive lateral velocity).
* **Flight Interface & Safety Boundary (V8)**: Monotonic command sequencing, rate limiting ($\le 25\text{Hz}$), and multi-layer authorization safety gates (`allow_external: false`).
* **Digital Twin & Scenario Validation (V9)**: 6-DoF vehicle kinematics, sensor noise models (Gaussian, random walk drift, bias, latency queues), Monte Carlo reproducibility, and deterministic scenario engine.

---

## 2. V1–V9 Subsystem Architecture

```
SkyVanta-AI/
├── .github/                      # CI/CD Workflows
│   └── workflows/ci.yml         # Matrix Regression Pipeline (Python 3.10-3.12)
├── skyvanta/                     # Production Modular Package
│   ├── core/                    # Immutable Types, Config Models, Exceptions, Logging
│   ├── perception/              # YOLO / Motion Detectors, Optical Flow, Candidate Fusion
│   ├── tracking/                # TrackManager, State Machine, One-Euro Filters
│   ├── target/                  # Fiducial Detectors (ArUco, AprilTag, Mock), PnP Estimator
│   ├── spatial/                 # SE(3) Transforms, Frame Graph, Camera Models, ENU/NED
│   ├── fusion/                  # 15-State ESEKF, IMU Preprocessor, SO(3) Math, Innovation Gate
│   ├── intelligence/            # 12-State Landing FSM, Safety Supervisor, Command Translation
│   ├── flight/                  # Flight Authorizer, Command Rate Limiter, Mock Autopilot
│   ├── simulation/              # Digital Twin Vehicle, Synthetic Sensors, Scenario Engine
│   └── pipeline/                # Video Ingestion, Demo Runner, HUD Compositor
├── config/                      # YAML Configuration Files
│   └── default.yaml             # Authoritative Platform Configuration
├── cpp/                         # Standalone C++ Subsystem & CMake Build
│   ├── CMakeLists.txt
│   └── src/main.cpp             # C++ Kalman Demo & HUD Drawing Engine
├── legacy/                      # Preserved Characterization Baseline Prototypes
│   ├── main.py
│   └── main.cpp
├── tests/                       # 250+ Automated Pytest Test Harness
│   ├── unit/                    # Subsystem Unit & Mathematical Invariant Tests
│   ├── integration/             # Closed-Loop Integration & V9 Regression Suites
│   └── characterization/       # Numerical Parity Against Baseline
├── pyproject.toml               # Python Packaging & Tool Configuration
├── requirements.txt             # Core Runtime Dependencies
└── requirements-dev.txt         # Development & Test Dependencies
```

---

## 3. Installation

### 1. Clone Repository
```bash
git clone https://github.com/luccy93/SkyVanta-AI.git
cd SkyVanta-AI
```

### 2. Install Dependencies
```bash
# Core production dependencies
pip install -r requirements.txt

# Development, testing, and linting tools
pip install -r requirements-dev.txt

# Editable package install
pip install -e .
```

---

## 4. Usage & Execution Modes

### 1. Execute Digital Twin Landing Scenario
Execute full closed-loop V9 landing scenarios directly via the canonical CLI:
```bash
# Nominal autonomous landing scenario
skyvanta --scenario nominal_landing

# Sensor dropout / visual occlusion abort scenario
skyvanta --scenario target_loss

# Turbulent descent with aerodynamic disturbance
skyvanta --scenario turbulent_descent
```

### 2. Run Monte Carlo Batch Validation
Run deterministic Monte Carlo simulations across multiple randomized seeds:
```bash
skyvanta --scenario high_winds --monte-carlo --runs 20 --seed 42
```

### 3. Run Simulation Performance Benchmark
```bash
skyvanta --benchmark-simulation
```

### 4. Synthetic Video Demonstration
Renders a synthetic aerial perception approach with HUD telemetry overlays to `output/demo_perception.mp4`:
```bash
skyvanta --demo
```

### 5. Process External Flight Video
```bash
skyvanta --input flight_footage.mp4 --output output/perception_annotated.mp4
```

---

## 5. Simulation Benchmarks & Scenarios

| Scenario Identifier | Focus & Environmental Condition | Primary Evaluated Invariant | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **`nominal_landing`** | Calm atmosphere, continuous target visibility | Steady alignment and smooth touchdown | `TOUCHDOWN` ($z \le 0.05\text{m}$, $v_z \le 0.3\text{m/s}$) |
| **`target_loss`** | 2.5-second complete target occlusion at $z=4\text{m}$ | Immediate transition to `ABORTING` climb | `ABORTED` (Climbs out at $v_z = +1.0\text{m/s}$) |
| **`high_winds`** | Continuous $1.2\text{m/s}$ lateral crosswind gusts | Lateral error hysteresis gating | Safe descent with active heading hold |
| **`sensor_dropout`** | Severe IMU / camera communication dropouts | Staleness detection ($> 0.5\text{s}$) | Transition to hold / abort mode |
| **`turbulent_descent`** | Rapid random-walk wind velocity impulses | ESEKF innovation gating ($\text{NIS} \le 16.81$) | Resilient covariance propagation |
| **`aborted_approach`** | Injected runaway velocity exceedance | Multi-layer velocity invariant protection | Guaranteed climb-out setpoint |
| **`severe_yaw_offset`** | Initial 45° angular misalignment | Geometric alignment verification ($\le 15^\circ$) | Heading alignment before descent |
| **`rapid_landing`** | Steep initial descent trajectory | Touchdown velocity damping ($\le 0.2\text{m/s}$) | Controlled soft landing |

### Typical Simulation Performance Benchmark (Core i7 / Ryzen):
* **Realtime Acceleration Factor**: $\approx 35\times - 65\times$ realtime
* **Simulation Step Latency**: $\approx 1.3\text{ ms}$ per step
* **Execution Throughput**: $> 750$ discrete closed-loop steps/second

---

## 6. Testing & Quality Assurance

Run the complete deterministic test suite:
```bash
pytest
```
The automated test suite runs **251+ tests** across:
* **Unit Tests**: Group Lie algebra $SO(3)$ & $SE(3)$, PnP geometry, 15-state ESEKF propagation/update, Chi2 innovation gating, 12-state FSM state machine transitions, rate limiter bypass invariants, ENU/NED coordinate transforms.
* **Integration Tests**: Full closed-loop digital twin execution, multi-sensor pipeline, scenario replay determinism, flight interface authorization gates.
* **Characterization Tests**: Numerical parity against legacy algorithms.

---

## 7. Safety Architecture & Operational Boundaries

> [!IMPORTANT]
> **Safety Boundary Notice**: SkyVanta AI is an offline, simulation-first software architecture.
> 1. **Hardware Isolation**: The codebase contains **zero** physical hardware drivers, serial port connections, UDP/TCP socket transports, or live MAVLink telemetry streams.
> 2. **Multi-Layer Safety Gate**: The parameter `flight_interface.safety.allow_external` defaults to `False`. External non-simulation command transmission is strictly prohibited by software invariant assertions.
> 3. **Offline Execution**: Automatic runtime network model downloads and runtime package installations are strictly disabled (`allow_network_download: false`).

---

## 8. Engineering Scope & Limitations

* **Simulation Results vs. Physical Avionics**: All benchmarks, state estimation trajectories, and landing evaluations documented in this repository represent **software-in-the-loop (SIL) simulation and digital twin validation**.
* **Flight Certification**: SkyVanta AI is an experimental robotics software platform and is **not certified** by the FAA, EASA, or any aviation authority for crewed or uncrewed physical flight operations.
* **No Real-World Flight Claims**: Simulation results demonstrate algorithmic correctness, numerical stability, and deterministic execution under synthetic disturbance models; they do not guarantee real-world flight performance or centimeter-level physical accuracy under unmodeled physical atmospheric dynamics.

---

## 9. Standalone C++ Subsystem

Build and execute the standalone OpenCV C++ HUD and Kalman engine:
```bash
cd cpp
mkdir build && cd build
cmake ..
cmake --build .
./skyvanta_cpp_demo
```

---

## 10. License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 **SkyVanta-AI / Devendraprasad**
