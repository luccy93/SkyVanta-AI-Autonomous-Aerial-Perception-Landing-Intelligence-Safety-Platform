"""Visual measurement Kalman update, error-state injection, and Joseph-form covariance reset."""

from typing import Optional, Tuple
import numpy as np

from skyvanta.core.config import ESEKFConfig
from skyvanta.core.types import VisualPoseMeasurement
from skyvanta.fusion.gating import InnovationGater
from skyvanta.fusion.so3 import so3_exp, so3_log
from skyvanta.fusion.state import ESEKFState, STATE_DIM


class KalmanUpdater:
    """Executes 6-DoF visual pose Kalman innovation, statistical gating, error injection, and covariance reset."""

    def __init__(self, config: Optional[ESEKFConfig] = None):
        self.config = config or ESEKFConfig()
        self.gater = InnovationGater(chi2_threshold=self.config.gating_threshold_chi2)

    def build_measurement_matrix(self) -> np.ndarray:
        """Constructs the 6x15 measurement Jacobian matrix H for direct position and attitude observations."""
        H = np.zeros((6, STATE_DIM), dtype=np.float64)
        # Position observation z_p = p
        H[0:3, 0:3] = np.eye(3)
        # Orientation observation Log(R^T * R_meas) = delta_theta
        H[3:6, 6:9] = np.eye(3)
        return H

    def get_measurement_covariance(self, measurement: VisualPoseMeasurement) -> np.ndarray:
        """Extracts or constructs the 6x6 measurement noise covariance matrix R_m."""
        if measurement.covariance is not None:
            R_m = np.array(measurement.covariance, dtype=np.float64)
            if R_m.shape == (6, 6) and np.all(np.isfinite(R_m)):
                return R_m

        # Construct from default standard deviations with quality weighting
        var_pos = (self.config.visual_pos_noise_std_m / max(0.1, measurement.quality)) ** 2
        var_att = (self.config.visual_att_noise_std_rad / max(0.1, measurement.quality)) ** 2

        R_m = np.zeros((6, 6), dtype=np.float64)
        R_m[0:3, 0:3] = np.eye(3) * var_pos
        R_m[3:6, 3:6] = np.eye(3) * var_att
        return R_m

    def update(
        self,
        state: ESEKFState,
        measurement: VisualPoseMeasurement,
    ) -> Tuple[ESEKFState, float, bool, Optional[str]]:
        """Executes full ESEKF visual pose correction cycle.

        Returns:
            (updated_state, nis_score, is_accepted, failure_reason)
        """
        p_meas = np.array(measurement.position_m, dtype=np.float64)
        R_meas = np.array(measurement.rotation_matrix, dtype=np.float64)

        # 1. Compute 6-Vector Residuals: r = [r_pos, r_att]^T
        r_pos = p_meas - state.p
        # Attitude residual in Body Lie algebra: Log(R_est^T * R_meas)
        r_att = so3_log(state.R.T @ R_meas)
        residual = np.concatenate([r_pos, r_att])

        # 2. Measurement Matrix & Innovation Covariance S
        H = self.build_measurement_matrix()
        R_m = self.get_measurement_covariance(measurement)
        S = H @ state.P @ H.T + R_m
        S = 0.5 * (S + S.T)  # Ensure exact symmetry

        # 3. Statistical Innovation Gating (NIS)
        nis, accepted, reason = self.gater.evaluate_gate(residual, S)
        if not accepted:
            return state, nis, False, reason

        # 4. Numerically Stable Kalman Gain: K = P * H^T * S^(-1)
        # Solve S * (H * P)^T = residual for stable gain computation
        # K = (np.linalg.solve(S, H @ state.P)).T
        K = state.P @ H.T @ np.linalg.inv(S)

        # 5. Error-State Vector Estimate: delta_x = K * r
        delta_x = K @ residual

        # 6. Error-State Injection into Nominal State
        p_updated = state.p + delta_x[0:3]
        v_updated = state.v + delta_x[3:6]
        R_updated = state.R @ so3_exp(delta_x[6:9])
        bg_updated = state.b_g + delta_x[9:12]
        ba_updated = state.b_a + delta_x[12:15]

        # 7. Joseph Form Covariance Reset
        I_KH = np.eye(STATE_DIM, dtype=np.float64) - K @ H
        P_updated = I_KH @ state.P @ I_KH.T + K @ R_m @ K.T
        P_updated = 0.5 * (P_updated + P_updated.T)

        updated_state = ESEKFState(
            position=(float(p_updated[0]), float(p_updated[1]), float(p_updated[2])),
            velocity=(float(v_updated[0]), float(v_updated[1]), float(v_updated[2])),
            rotation_matrix=R_updated,
            gyro_bias=(float(bg_updated[0]), float(bg_updated[1]), float(bg_updated[2])),
            accel_bias=(float(ba_updated[0]), float(ba_updated[1]), float(ba_updated[2])),
            timestamp_sec=measurement.timestamp_sec,
            covariance=P_updated,
            status=state.status,
        )

        return updated_state, nis, True, None
