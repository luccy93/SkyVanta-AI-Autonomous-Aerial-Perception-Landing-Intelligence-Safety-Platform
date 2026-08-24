# ADR-0002: Multi-Target Tracking & State Estimation Architecture

## Status
**ACCEPTED** (2026-08-24)

## Context
Volume 3 requires a multi-target tracking subsystem to bridge raw object detections and high-level 3D spatial estimation. Aerial drone landing perception presents specific tracking challenges:
1. High-frequency image-space jitter from drone attitude changes and vibration.
2. Intermittent visual occlusions and false-negative detector drops.
3. Strict real-time compute budget on edge hardware (Jetson / Raspberry Pi).
4. Need for clean decoupling between kinematic prediction, measurement filtering, and visual smoothing.

Candidate architectures considered:
* **Option A**: DeepSORT / ByteTrack with deep feature embedding re-identification.
* **Option B**: Coupled Kalman + EMA filter in a single monolithic class.
* **Option C (Selected)**: Modular 8-state Linear Kalman Filter + Decoupled One Euro Visual Smoothing + Deterministic 6-State FSM + Spatial-Gated IoU Data Association.

## Decision
We chose **Option C**:
1. **IoU Matching with Spatial Gating**: Lightweight, deterministic, and highly efficient for aerial targets with consistent bounding boxes, avoiding the heavy GPU inference overhead of appearance-based Re-ID networks.
2. **8-State Linear Kalman Filter in Image Space**: Tracks position, dimensions, and image-space velocities $(\dot{x}, \dot{y}, \dot{w}, \dot{h})$ to maintain accurate coasting predictions during occlusions.
3. **Decoupled One Euro Adaptive Smoothing**: Post-Kalman visual smoothing removes pixel jitter without distorting the underlying filter covariance or state propagation.
4. **Deterministic 6-State Lifecycle Machine**: Strict state transitions (`TENTATIVE` $\to$ `CONFIRMED` $\to$ `TRACKING` $\to$ `COASTING` $\to$ `LOST` $\to$ `DELETED`) prevent false-positive ghost tracks and enforce clean track recovery.

## Consequences
* **Positive**:
  - Sub-millisecond execution latency per frame ($< 1.0\text{ms}$ on CPU).
  - 100% deterministic, offline-testable with zero GPU/CUDA dependencies.
  - Clear architectural boundaries for future Volume 4 PnP and Volume 6 ESEKF.
* **Negative / Limitations**:
  - Does not resolve severe target identity swaps when multiple identical visual targets cross directly over each other in close proximity (which will be resolved when fiducial ID decoding and 3D PnP geometry are introduced in Volume 4).
