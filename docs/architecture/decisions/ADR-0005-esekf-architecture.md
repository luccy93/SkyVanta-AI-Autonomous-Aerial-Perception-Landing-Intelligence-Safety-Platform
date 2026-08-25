# ADR-0005: 15-State Error-State Extended Kalman Filter (ESEKF) Architecture

## Status
**ACCEPTED** (2026-08-25)

## Context
In Volumes 4 and 5, SkyVanta AI introduced landing pad fiducial perception, 6-DoF Perspective-n-Point pose estimation, and $\mathbb{SE}(3)$ coordinate transformations.
However, visual pose measurements are discrete (20–30 Hz), subject to occlusions, latency, and noise. Inertial Measurement Units (IMUs) provide high-rate (100–400 Hz) kinematic measurements but suffer from unbounded integration drift and sensor bias.

A state estimator was needed to fuse IMU measurements with discrete visual pose observations to produce continuous, optimal platform state estimates.

## Decision

1. **Error-State Extended Kalman Filter (ESEKF) Over Standard EKF**:
   - Rather than tracking attitude in a non-minimal parameterization (e.g. 4D quaternion) directly within the Kalman state vector, we track the **true nominal state** on the manifold $\mathbb{R}^3 \times \mathbb{R}^3 \times \mathbb{SO}(3) \times \mathbb{R}^3 \times \mathbb{R}^3$ and model uncertainty in a **minimal 15-dimensional error state** $\delta \mathbf{x} = [\delta \mathbf{p}, \delta \mathbf{v}, \delta \boldsymbol{\theta}, \delta \mathbf{b}_g, \delta \mathbf{b}_a]^T \in \mathbb{R}^{15}$.
   - This avoids quaternion normalization constraints during the update step and maintains full covariance rank.

2. **SO(3) Lie Algebra Attitude Parameterization**:
   - Attitude errors $\delta \boldsymbol{\theta} \in \mathbb{R}^3$ are mapped into $\mathbb{SO}(3)$ using the exact Rodrigues Exponential map $\text{Exp}(\delta \boldsymbol{\theta})$, with second-order Taylor series for small-angle numerical stability ($< 10^{-6}$).
   - Orientation residuals are calculated via the logarithmic map $\text{Log}(\mathbf{R}_{\text{est}}^T \mathbf{R}_{\text{meas}})$.

3. **Joseph-Form Covariance Reset**:
   - Updates utilize the Joseph stabilized formulation:
     $$P \leftarrow (\mathbf{I} - K H) P (\mathbf{I} - K H)^T + K R_m K^T$$
     guaranteeing positive semi-definiteness ($P \succ 0$) and symmetry under finite-precision arithmetic.

4. **Statistical Innovation Gating (NIS)**:
   - All measurements pass through a Normalized Innovation Squared (NIS) Mahalanobis distance test against a 6-DoF $\chi^2$ gate ($\alpha=0.01$, threshold 16.81) before updating state or covariance.

## Consequences

* **Positive**:
  - Unbounded IMU drift eliminated by visual pose corrections.
  - Sub-decimeter position tracking accuracy ($< 0.05$ m RMSE in nominal synthetic tests).
  - High performance: IMU propagation executes in ~124 µs (~8,000 Hz throughput).
  - Robust rejection of visual outliers.

* **Negative / Trade-offs**:
  - IMU sample timestamps must be strictly monotonic ($dt > 0$); timestamp jitter or out-of-order samples require rejection.
