"""Innovation computation, statistical Mahalanobis distance gating, and outlier rejection."""

from typing import Optional, Tuple
import numpy as np


class InnovationGater:
    """Performs statistical Normalized Innovation Squared (NIS) gating for measurement validation."""

    def __init__(self, chi2_threshold: float = 16.81):
        self.chi2_threshold = float(chi2_threshold)

    def evaluate_gate(
        self,
        residual: np.ndarray,
        innovation_covariance: np.ndarray,
    ) -> Tuple[float, bool, Optional[str]]:
        """Computes Mahalanobis NIS distance and determines whether the measurement passes the statistical gate.

        Args:
            residual: (M,) innovation residual vector r = z - h(x).
            innovation_covariance: (M, M) innovation covariance S = H * P * H^T + R_m.

        Returns:
            (nis_score, is_accepted, failure_reason)
        """
        r = np.ascontiguousarray(residual, dtype=np.float64).flatten()
        S = np.ascontiguousarray(innovation_covariance, dtype=np.float64)

        if not np.all(np.isfinite(r)) or not np.all(np.isfinite(S)):
            return float("inf"), False, "Non-finite values detected in residual or innovation covariance"

        try:
            # Solve S * x = r for x = S^(-1) * r stably
            S_inv_r = np.linalg.solve(S, r)
            nis = float(r @ S_inv_r)

            if not np.isfinite(nis) or nis < 0.0:
                return float("inf"), False, f"Invalid numerical NIS value: {nis}"

            if nis > self.chi2_threshold:
                return nis, False, f"Measurement NIS {nis:.2f} exceeds Chi-squared gate ({self.chi2_threshold:.2f})"

            return nis, True, None

        except np.linalg.LinAlgError as e:
            return float("inf"), False, f"Singular or degenerate innovation covariance matrix: {e}"
