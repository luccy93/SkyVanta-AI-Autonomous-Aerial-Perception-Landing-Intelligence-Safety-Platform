# SkyVanta AI — Architectural Decisions & Deep-Dive Explanation

## 1. Architectural Philosophy

The architecture of **SkyVanta AI** is driven by three foundational principles:
1. **Mathematical Rigor Over Heuristics:** State estimation and pose calculations utilize formal Lie-group manifolds ($SO(3)$) and optimal estimation theory rather than empirical filters.
2. **Defensive Safety by Design:** Safety supervisors operate as deterministic finite state machines with formal invariant guards (`ABORT -> never DESCEND`), eliminating ambiguous state transitions.
3. **Strict Separation of Core & Deployment:** The algorithmic robotics core (Volumes V1–V9) is self-contained and frozen, while the deployment layer (Phases D1–D9) wraps the core in a hardened, observable, and authenticated cloud runtime.

---

## 2. Deep-Dive: Key Architectural Decisions

### Decision 1: Manifold-Based 15-State Error-State EKF (Volume V6)
* **Problem:** Standard Extended Kalman Filters parameterizing 3D attitude with Euler angles suffer from gimbal lock at $\pm 90^\circ$ pitch. Parameterizing with 4D unit quaternions introduces constraint violation ($\|\mathbf{q}\| \neq 1$) and covariance matrix rank deficiency (a $4\times4$ covariance matrix for a 3-DoF rotation).
* **Solution:** SkyVanta implements a continuous-discrete Error-State EKF on the $SO(3)$ manifold:
  - The **nominal state** $\mathbf{x} = [\mathbf{p}, \mathbf{v}, \mathbf{q}, \mathbf{b}_a, \mathbf{b}_g]^T$ evolves via true non-linear kinematics.
  - The **error state** $\delta\mathbf{x} = [\delta\mathbf{p}, \delta\mathbf{v}, \delta\boldsymbol{\theta}, \delta\mathbf{b}_a, \delta\mathbf{b}_g]^T \in \mathbb{R}^{15}$ operates in a linear tangent space around the nominal state.
  - The error rotation vector $\delta\boldsymbol{\theta} \in \mathbb{R}^3$ represents an unconstrained perturbation in the Lie algebra $\mathfrak{so}(3)$.
  - After measurement updates, the error state is injected into the nominal state:
    $$\mathbf{q} \leftarrow \mathbf{q} \otimes \begin{bmatrix} 1 \\ \frac{1}{2}\delta\boldsymbol{\theta} \end{bmatrix}, \quad \mathbf{p} \leftarrow \mathbf{p} + \delta\mathbf{p}, \quad \mathbf{v} \leftarrow \mathbf{v} + \delta\mathbf{v}$$
    and $\delta\mathbf{x}$ is reset to zero.

---

### Decision 2: Monocular 6-DoF Perspective-n-Point Pose Estimation (Volume V4)
* **Problem:** Monocular cameras do not provide native depth. Recovering relative 3D translation and 3D orientation requires matching known object geometry to 2D image coordinates.
* **Solution:** We implement a calibrated PnP pipeline with SQPnP and planar IPPE algorithms:
  - 4 coplanar fiducial corners with known model coordinates in target frame $\mathbf{P}_i^t = [X_i, Y_i, 0]^T$.
  - 2D pixel detections $\mathbf{u}_i = [u_i, v_i]^T$ are normalized using the camera intrinsic calibration matrix $\mathbf{K}$:
    $$\tilde{\mathbf{x}}_i = \mathbf{K}^{-1} \begin{bmatrix} u_i \\ v_i \\ 1 \end{bmatrix}$$
  - SQPnP solves for $\mathbf{R}_c^t \in SO(3)$ and $\mathbf{t}_c^t \in \mathbb{R}^3$ by globally minimizing algebraic and geometric reprojection errors:
    $$\min_{\mathbf{R}, \mathbf{t}} \sum_{i=1}^{4} \left\| \tilde{\mathbf{x}}_i - \frac{\mathbf{R} \mathbf{P}_i^t + \mathbf{t}}{\mathbf{e}_3^T (\mathbf{R} \mathbf{P}_i^t + \mathbf{t})} \right\|^2$$

---

### Decision 3: Deterministic 12-State Safety Supervisor (Volume V7)
* **Problem:** Autonomous descent during sensor failure, high covariance, or target loss leads to catastrophic vehicle crashes.
* **Solution:** The Safety Supervisor operates as an explicit Finite State Machine with strictly audited transition rules:
  - Phase progression: `SEARCHING` $\rightarrow$ `TARGET_ACQUIRED` $\rightarrow$ `ALIGNING` $\rightarrow$ `APPROACHING` $\rightarrow$ `DESCENDING` $\rightarrow$ `FINAL_APPROACH` $\rightarrow$ `LANDING_CONFIRMED`.
  - At any phase, if target tracking is lost or 3-sigma position covariance exceeds threshold ($\sigma_{\text{pos}} > 0.25\text{ m}$), the FSM immediately transitions to `ABORTING`.
  - **Hard Invariant:** `ABORTING` can only transition to `RECOVERY`, `FAULT`, or `IDLE`. Transition to `DESCENDING` or `FINAL_APPROACH` is mathematically impossible in the state transition table.

---

### Decision 4: Tiered Cryptographic Security & Non-Blocking WebSockets (Phases D3, D8)
* **Problem:** High-rate telemetry streaming (20 Hz) to multiple dashboard clients must not block simulation computation, leak credentials, or allow unauthorized scenario execution.
* **Solution:**
  - Role-based API key authentication (`Scope.READ`, `Scope.EXECUTE`, `Scope.ADMIN`) with constant-time SHA-256 validation (`hmac.compare_digest`).
  - Asynchronous broadcast queue per connected WebSocket client with bounded capacity (`maxsize=50`).
  - Slow or stalling network clients trigger automatic frame dropping and disconnection without backpressure propagating to the simulation engine.

---

### Decision 5: Non-Root Hardened OCI Container & Dropped Capabilities (Phase D4)
* **Problem:** Running robotics software in cloud containers with default root permissions introduces security vulnerabilities.
* **Solution:**
  - Multi-stage Dockerfile compiling wheels in a builder stage and copying only runtime dependencies to a minimal runtime container.
  - Dedicated unprivileged system user `skyvanta` (UID 1000).
  - Explicit Linux capability dropping (`cap_drop: [ALL]`) and privilege escalation blocking (`no-new-privileges:true`).
  - Read-only container root support with explicit tmpfs mounts for `/tmp`.
