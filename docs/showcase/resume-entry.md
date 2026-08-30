# SkyVanta AI — Resume Entry Formats & Project Descriptions

Use the appropriate version below based on resume format, space constraints, and job target.

---

## 1. One-Line Version (Compact Resume / Summary)

> **SkyVanta AI:** Architected a software-in-the-loop autonomous aerial landing intelligence and 6-DoF digital twin platform featuring a 15-state Error-State EKF ($SO(3)$), monocular PnP pose estimation, and a hardened FastAPI/WebSocket deployment with 437+ automated tests.

---

## 2. Two-Line Version (Standard Experience / Projects Section)

> **SkyVanta AI — Autonomous Aerial Perception & Digital Twin Platform**  
> Engineered a mission-critical autonomous landing perception platform integrating computer vision (PnP 6-DoF), a 15-state Error-State Extended Kalman Filter on Lie-group $SO(3)$, and a 12-state deterministic safety supervisor. Deployed via a hardened multi-stage Docker container with 20 Hz WebSocket telemetry streaming, API key security, and 100% pass across 437+ automated tests.

---

## 3. Three-Bullet Version (Detailed Resume Format)

> **SkyVanta AI — Autonomous Aerial Perception, State Estimation & Digital Twin Service**
> * **State Estimation & 6-DoF Pose:** Implemented a continuous-discrete 15-state Error-State Extended Kalman Filter (ESEKF) on the Lie-group $SO(3)$ manifold fused with monocular SQPnP/IPPE pose estimation, achieving sub-centimeter touchdown accuracy in GPS-denied simulation benchmarks.
> * **Deterministic Safety Supervision:** Designed a 12-state finite state machine enforcing strict covariance gating ($\sigma_{\text{pos}} < 0.25\text{ m}$) and non-negotiable abort invariants (`ABORT -> never DESCEND`), backed by a 56x real-time 6-DoF digital twin physics engine.
> * **Cloud Deployment & Reliability:** Deployed a production-hardened FastAPI service with 20 Hz WebSocket telemetry streaming, constant-time SHA-256 API authentication, rate limiting, automated pre-flight release verification, and disaster recovery runbooks (437+ tests, 100% pass).

---

## 4. Technical Interview Explanation (1-Minute Elevator Pitch)

> "SkyVanta AI is an enterprise-grade software-in-the-loop autonomous aerial landing platform designed for GPS-denied operations.
>
> On the robotics side, I built a 15-state Error-State Extended Kalman Filter operating directly on the Lie-group $SO(3)$ rotation manifold to avoid gimbal lock and quaternion singularities. This filter fuses 100 Hz IMU kinematics with 6-DoF pose estimates from a monocular Perspective-n-Point vision solver. A 12-state safety state machine supervises vehicle kinematics and guarantees that descent is locked out if estimation covariance rises or the target is lost.
>
> On the deployment side, I built a hardened, unprivileged Docker service on FastAPI and WebSockets that streams real-time vehicle telemetry at 20 Hz with token-bucket rate limiting and zero-overhead observability. The entire platform is backed by 437 automated regression tests and pre-flight release verification gates."
