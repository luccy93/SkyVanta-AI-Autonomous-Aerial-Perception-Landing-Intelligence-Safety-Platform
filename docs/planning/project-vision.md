# SkyVanta AI — Project Vision & Mission

## 1. Vision Statement
**SkyVanta AI** is an autonomous aerial perception, landing intelligence, and safety verification platform. It bridges the critical reliability gap in autonomous Unmanned Aerial Vehicle (UAV) terminal operations by transforming raw monocular, stereo, and multimodal sensor feeds into deterministic, safety-bounded landing decisions.

The overarching vision of SkyVanta AI is to enable **zero-incident, vision-guided autonomous landing across unmapped, GPS-degraded, dynamically moving, and adverse visual environments** through a multi-tier fusion of deep learning perception, geometric state estimation, real-time deterministic safety supervisor logic, and standardized flight controller interfaces.

---

## 2. The Core Problem
Autonomous landing remains the most hazardous and failure-prone phase of UAV flight operations:
* **GPS Vulnerabilities**: GPS jamming, spoofing, multi-path reflections near structures, and vertical dilution of precision (VDOP) make raw satellite navigation inadequate for centimetre-accurate touchdown.
* **Dynamic & Moving Platforms**: Landing on maritime vessels, moving ground vehicles, or oscillating offshore platforms requires continuous relative pose tracking and predictive motion compensation.
* **Perceptual Degradation**: Environmental challenges—such as motion blur from wind shear, low illumination, ground reflection, dust/rotor wash, and sudden visual occlusion—cause brittle deep learning detectors to produce false positives or dropped tracks.
* **The "Black Box" Safety Problem**: Direct end-to-end neural network flight control lacks deterministic guarantees. Without formal safety supervisors, neural network hallucinations or confidence spikes during visual loss can result in catastrophic crashes.

---

## 3. Target Audience & Stakeholders
1. **Commercial Drone Delivery & Logistics Operators**: Demanding automated precision landing on charging pads, hub lockers, and constrained residential drop zones.
2. **Industrial & Infrastructure Inspection Teams**: Requiring reliable recovery of autonomous inspection drones on oil rigs, power stations, and cell towers without human pilots.
3. **Defense, Search & Rescue (SAR), and Maritime Operators**: Operating in GPS-denied tactical environments, austere forward operating bases, and dynamic naval vessel decks.
4. **Autonomous Robotics Researchers & OEMs**: Needing a modular, standardized aerial perception and safety stack that interfaces with PX4/ArduPilot via MAVLink.

---

## 4. Key Value Propositions & Technical Significance
* **Tri-Tier Perception Architecture**: Combines fiducial markers (ArUco/AprilTag Level 1), geometric-visual pad detection (Level 2), and semantic segmentation with temporal tracking (Level 3).
* **Deterministic Safety Isolation**: Complete architectural decoupling between AI perception recommendations and the deterministic Safety Supervisor. The safety supervisor enforces hard boundary envelopes (velocity, drift, tilt, descent rate, sensor health) and can veto AI predictions at any millisecond.
* **Hardware-Agnostic Edge-First Design**: Optimized for low-SWaP (Size, Weight, and Power) edge compute (NVIDIA Jetson Orin Nano/NX, Raspberry Pi 5) with zero dependence on cloud infrastructure for real-time perception and flight-critical decision loops.
* **Progressive Verification Paradigm**: Structured development lifecycle spanning pure Python/C++ simulation, PX4 SITL with Gazebo/AirSim, Hardware-in-the-Loop (HIL), and tethered/geofenced field validation.

---

## 5. End-State Demonstration Goal
The final milestone demonstration of SkyVanta AI will exhibit:
1. **Autonomous Mission Initiation**: Drone reaches the terminal approach area under GPS-denied simulation/SITL conditions.
2. **Visual Target Acquisition**: Onboard edge vision pipeline detects the landing site from high altitude (>25m) using semantic search.
3. **Pad Transition & Precision Locking**: Pipeline transitions to Level 2/Level 1 geometric landing-pad pose estimation, achieving sub-5cm tracking precision.
4. **Kalman-Filtered State Fusion**: Fuses vision pose with IMU, rangefinder/barometer, and optical flow at 50+ Hz with quantified covariance/uncertainty bounds.
5. **Dynamic Approach Corridor & Alignment**: Real-time trajectory projection, glide-slope monitoring, and attitude alignment.
6. **Active Fault Injection & Failsafe Execution**: Injection of visual occlusion, pad drift, and sensor timeout scenarios showing autonomous `HOLD` and `ABORT` triggers with zero hard-impact crashes.
7. **Smooth Autonomous Touchdown & Mission Analytics**: Controlled touchdown within 5cm of pad center, followed by automated telemetry log generation, safety audit trails, and post-flight AI assistant debriefing.
