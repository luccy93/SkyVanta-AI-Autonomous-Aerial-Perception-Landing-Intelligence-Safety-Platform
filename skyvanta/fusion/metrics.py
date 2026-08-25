import math
from typing import Any, Dict, List
import numpy as np


from skyvanta.fusion.so3 import so3_geodesic_distance


class StateEstimationMetrics:
    """Calculates root-mean-square errors and Lie group rotation errors between estimate and ground truth."""

    @staticmethod
    def evaluate(
        estimates: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Computes comprehensive trajectory tracking error metrics."""
        if len(estimates) != len(ground_truth) or len(estimates) == 0:
            raise ValueError("Estimates and ground truth list lengths must match and be non-empty")

        pos_errors = []
        vel_errors = []
        att_errors_deg = []
        bg_errors = []
        ba_errors = []

        for est, gt in zip(estimates, ground_truth):
            # Position error
            p_est = np.array(est["position"])
            p_gt = np.array(gt["position"])
            pos_errors.append(np.linalg.norm(p_est - p_gt))

            # Velocity error
            v_est = np.array(est["velocity"])
            v_gt = np.array(gt["velocity"])
            vel_errors.append(np.linalg.norm(v_est - v_gt))

            # Orientation geodesic distance on SO(3)
            R_est = np.array(est["rotation"])
            R_gt = np.array(gt["rotation"])
            dist_rad = so3_geodesic_distance(R_est, R_gt)
            att_errors_deg.append(math.degrees(dist_rad))

            # Bias errors if available
            if "gyro_bias" in est and "gyro_bias" in gt:
                bg_est = np.array(est["gyro_bias"])
                bg_gt = np.array(gt["gyro_bias"])
                bg_errors.append(np.linalg.norm(bg_est - bg_gt))

            if "accel_bias" in est and "accel_bias" in gt:
                ba_est = np.array(est["accel_bias"])
                ba_gt = np.array(gt["accel_bias"])
                ba_errors.append(np.linalg.norm(ba_est - ba_gt))

        metrics = {
            "position_rmse_m": float(np.sqrt(np.mean(np.array(pos_errors) ** 2))),
            "velocity_rmse_m_s": float(np.sqrt(np.mean(np.array(vel_errors) ** 2))),
            "orientation_rmse_deg": float(np.sqrt(np.mean(np.array(att_errors_deg) ** 2))),
            "max_position_error_m": float(np.max(pos_errors)),
            "max_orientation_error_deg": float(np.max(att_errors_deg)),
        }

        if bg_errors:
            metrics["gyro_bias_rmse_rad_s"] = float(np.sqrt(np.mean(np.array(bg_errors) ** 2)))
        if ba_errors:
            metrics["accel_bias_rmse_m_s2"] = float(np.sqrt(np.mean(np.array(ba_errors) ** 2)))

        return metrics
