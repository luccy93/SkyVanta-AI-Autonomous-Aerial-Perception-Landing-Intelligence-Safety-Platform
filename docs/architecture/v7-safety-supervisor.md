# SkyVanta AI — Volume 7 Safety Supervisor Specification

---

## 1. Safety Invariants

| Invariant | Evaluated Quantity | Safety Gate Condition | Default Limit | Failure Reason Code |
| :--- | :--- | :--- | :--- | :--- |
| **INV-1** | Estimator Health | `status == INITIALIZED` and `age <= max_age` | $\le 0.5\text{ s}$ | `ESTIMATOR_UNINITIALIZED` / `ESTIMATOR_STALE` |
| **INV-2** | Target Health | `is_valid == True` and `age <= max_age` | $\le 0.5\text{ s}$ | `TARGET_NOT_FOUND` / `TARGET_STALE` |
| **INV-3** | Target Quality | `reprojection_error_rms <= 5.0 px` | $\le 5.0\text{ px}$ | `REPROJECTION_ERROR_HIGH` |
| **INV-4** | Position Uncertainty | $3\sigma_{\text{pos}} \le \text{max\_pos\_sigma}$ | $\le 0.5\text{ m}$ (descent) / $\le 0.2\text{ m}$ (final) | `POSITION_UNCERTAINTY_HIGH` |
| **INV-5** | Velocity Uncertainty | $3\sigma_{\text{vel}} \le \text{max\_vel\_sigma}$ | $\le 0.5\text{ m/s}$ | `VELOCITY_UNCERTAINTY_HIGH` |
| **INV-6** | Orientation Uncertainty | $3\sigma_{\text{att}} \le \text{max\_att\_sigma}$ | $\le 5.0\text{ deg}$ | `ORIENTATION_UNCERTAINTY_HIGH` |
| **INV-7** | Horizontal Velocity | $v_{\text{xy}} \le \text{max\_horiz\_speed}$ | $\le 2.0\text{ m/s}$ (descent) / $\le 0.5\text{ m/s}$ (final) | `VELOCITY_TOO_HIGH` |
| **INV-8** | Vertical Velocity | $|v_z| \le \text{max\_descent\_speed}$ | $\le 1.0\text{ m/s}$ (descent) / $\le 0.3\text{ m/s}$ (final) | `VELOCITY_TOO_HIGH` |
| **INV-9** | Lateral Offset | $|\Delta x| \le \text{max\_lateral\_error}$ | $\le 1.5\text{ m}$ (align) / $\le 0.3\text{ m}$ (final) | `LATERAL_ERROR_TOO_HIGH` |
| **INV-10** | Heading Offset | $|\Delta \psi| \le \text{max\_yaw\_error}$ | $\le 15.0\text{ deg}$ (align) / $\le 5.0\text{ deg}$ (final) | `YAW_ERROR_TOO_HIGH` |
| **INV-11** | Touchdown Persistence | $N_{\text{consecutive}} \ge N_{\text{required}}$ | $\ge 10\text{ frames}$ | `PERSISTENCE_INSUFFICIENT` |

---

## 2. Deterministic Abort Hierarchy

When multiple invariant breaches occur concurrently, the supervisor applies strict deterministic priority ordering:

1. **`CRITICAL_FAULT`**: Immediate hardware fault or unrecoverable error flag.
2. **`ESTIMATOR_UNINITIALIZED` / `ESTIMATOR_STALE`**: Missing or degraded navigation filter.
3. **`TARGET_LOST` / `TARGET_NOT_FOUND` / `POSE_STALE`**: Loss of optical fiducial reference.
4. **`POSITION_UNCERTAINTY_HIGH` / `VELOCITY_UNCERTAINTY_HIGH`**: Filter covariance explosion.
5. **`VELOCITY_TOO_HIGH`**: Platform exceeding safe aerodynamic descent limits.
6. **`LATERAL_ERROR_TOO_HIGH` / `LONGITUDINAL_ERROR_TOO_HIGH` / `YAW_ERROR_TOO_HIGH`**: Target corridor deviation.
7. **`STATE_TIMEOUT`**: Phase duration exceeded.
