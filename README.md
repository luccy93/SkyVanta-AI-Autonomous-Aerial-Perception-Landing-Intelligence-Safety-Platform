# SkyVanta AI — Autonomous Aerial Perception, Landing Intelligence & Safety Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-25%20passed-brightgreen.svg)](tests/)

**Developer / Creator:** SkyVanta-AI / Devendraprasad  
**Repository:** [https://github.com/luccy93/SkyVanta-AI](https://github.com/luccy93/SkyVanta-AI)

---

## Overview

**SkyVanta AI** is a modular computer vision, visual target tracking, and autonomous aerial perception platform designed for drone landing intelligence, relative approach geometry estimation, and tactical situational awareness.

The platform provides:
* **Hybrid Visual Detection**: Multi-cue candidate fusion combining YOLO deep learning inference with MOG2 background subtraction, Farneback dense optical flow, and Canny edge density scoring.
* **Persistent State Estimation**: Linear 2D Kalman filter with dual One-Euro adaptive low-pass filters for zero-latency jitter reduction.
* **Tactical Approach Corridor**: Perspective-aware 3D-style trapezoidal approach guidance tunnel dynamically projected to the ground landing pad.
* **Visual Telemetry Readouts**: Heuristic visual distance, altitude, lateral/vertical offset, approach angle, and alignment estimations.
* **Modular Python Package & C++ Subsystem**: Clean `skyvanta` package with typed Pydantic data structures, YAML configuration, CLI runner, and CMake C++ subsystem.

---

## System Architecture (Volume 1)

```
SkyVanta-AI/
├── skyvanta/                     # Core Modular Python Package
│   ├── core/                    # Types, Config, Logging, Exceptions
│   ├── perception/              # YOLO & Motion Contrast Detectors + Fusion
│   ├── tracking/                # KalmanBox2D, OneEuroFilter, TrackStateMachine
│   ├── telemetry/               # TelemetryEstimator (heuristic visual metrics)
│   ├── visualization/           # Palette, Drawing Primitives, Corridor, HUD Compositor
│   ├── simulation/              # Procedural Aerial Scene & Demo Generator
│   └── pipeline/                # PipelineRunner & Ingestion Orchestrator
├── cpp/                         # Standalone C++ Subsystem & CMake Build
│   ├── CMakeLists.txt
│   └── src/main.cpp
├── config/                      # YAML Configuration Files
│   └── default.yaml
├── legacy/                      # Preserved Baseline Prototypes
│   ├── main.py
│   └── main.cpp
├── tests/                       # Pytest Suite (Unit, Integration, Parity)
│   ├── unit/
│   ├── integration/
│   └── characterization/
├── pyproject.toml               # Modern Python Package Specification
└── requirements.txt             # Locked Dependencies
```

---

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/luccy93/SkyVanta-AI.git
cd SkyVanta-AI
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

For development and test dependencies:
```bash
pip install -r requirements-dev.txt
```

---

## Usage

### 1. Run Procedural Synthetic Demonstration
```bash
python -m skyvanta --demo
# or simply:
python -m skyvanta
```
Renders a 13-second synthetic aerial approach demonstration to `output/demo_perception.mp4`.

### 2. Process Input Video File
```bash
python -m skyvanta --input path/to/flight_video.mp4 --output output/rendered_perception.mp4
```

### 3. Custom Configuration
```bash
python -m skyvanta --input flight.mp4 --config config/default.yaml
```

### 4. Detection Mode Flags
* Force enable YOLO object detection: `python -m skyvanta --yolo`
* Disable YOLO (motion-contrast only): `python -m skyvanta --no-yolo`

---

## Testing & Quality Assurance

Run the automated test harness:
```bash
pytest
```
The test harness runs 25 automated tests across:
* **Unit Tests**: Bounding box geometry, IoU calculation, configuration serialization, Kalman predict/correct cycles, One-Euro low-pass filtering, tracking FSM transitions.
* **Integration Tests**: End-to-end video pipeline synthesis without crashes.
* **Characterization Tests**: Numerical and mathematical parity verification against baseline algorithms.

---

## Standalone C++ Subsystem

Build and execute the C++ Kalman bouncing ball and HUD rendering demo:
```bash
cd cpp
mkdir build && cd build
cmake ..
cmake --build .
./skyvanta_cpp_demo
```

---

## Legacy Prototype Archive

The original monolithic prototype files are preserved in `legacy/`:
* `legacy/main.py`: `python legacy/main.py [video.mp4]`
* `legacy/main.cpp`: Standalone OpenCV C++ prototype

---

## Disclaimer

SkyVanta AI Volume 1 is an experimental computer vision and software perception platform. Telemetry metrics (distance, altitude, angle, alignment) are derived from 2D visual heuristics and pixel scale changes. They represent visual approximations for simulation and HUD display, not certified physical avionics measurements.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 **SkyVanta-AI / Devendraprasad**
