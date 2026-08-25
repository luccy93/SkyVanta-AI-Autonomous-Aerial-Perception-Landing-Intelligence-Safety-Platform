"""Lie group SO(3) and Lie algebra so(3) mathematical operations for ESEKF."""

import math
import numpy as np


def skew_symmetric(v: np.ndarray) -> np.ndarray:
    """Computes the 3x3 skew-symmetric matrix [v]_x from a 3-vector.

    [v]_x = [  0  -vz   vy ]
            [  vz   0  -vx ]
            [ -vy  vx   0  ]
    """
    vx, vy, vz = float(v[0]), float(v[1]), float(v[2])
    return np.array([
        [0.0, -vz, vy],
        [vz, 0.0, -vx],
        [-vy, vx, 0.0],
    ], dtype=np.float64)


def so3_exp(v: np.ndarray) -> np.ndarray:
    """Exponential map Exp: so(3) -> SO(3) mapping rotation vector to 3x3 rotation matrix.

    Uses Rodrigues' formula with small-angle Taylor expansion for ||v|| < 1e-6.
    """
    vec = np.ascontiguousarray(v, dtype=np.float64).flatten()
    theta = float(np.linalg.norm(vec))

    if theta < 1e-6:
        # Second-order Taylor series: Exp(v) ≈ I + [v]_x + 0.5 * [v]_x^2
        K = skew_symmetric(vec)
        return np.eye(3, dtype=np.float64) + K + 0.5 * (K @ K)

    K = skew_symmetric(vec / theta)
    return np.eye(3, dtype=np.float64) + math.sin(theta) * K + (1.0 - math.cos(theta)) * (K @ K)


def so3_log(R: np.ndarray) -> np.ndarray:
    """Logarithmic map Log: SO(3) -> so(3) mapping a 3x3 rotation matrix to a 3-vector rotation angle.

    Extracts the minimal rotation vector v in R^3 such that Exp(v) = R.
    """
    R_mat = np.ascontiguousarray(R, dtype=np.float64).reshape(3, 3)
    cos_theta = (np.trace(R_mat) - 1.0) / 2.0
    cos_theta = max(-1.0, min(1.0, cos_theta))  # Clamp for numerical stability
    theta = math.acos(cos_theta)

    if theta < 1e-6:
        # Small-angle approximation: Log(R) ≈ 0.5 * [R - R^T]_vee
        return np.array([
            0.5 * (R_mat[2, 1] - R_mat[1, 2]),
            0.5 * (R_mat[0, 2] - R_mat[2, 0]),
            0.5 * (R_mat[1, 0] - R_mat[0, 1]),
        ], dtype=np.float64)

    sin_theta = math.sin(theta)
    if abs(sin_theta) < 1e-6:
        # theta ≈ pi (180-degree rotation)
        diag = np.diag(R_mat)
        k = np.argmax(diag)
        col = R_mat[:, k]
        col[k] += 1.0
        v_norm = np.linalg.norm(col)
        axis = col / v_norm if v_norm > 0 else np.array([1.0, 0.0, 0.0])
        return axis * theta

    factor = theta / (2.0 * sin_theta)
    return np.array([
        factor * (R_mat[2, 1] - R_mat[1, 2]),
        factor * (R_mat[0, 2] - R_mat[2, 0]),
        factor * (R_mat[1, 0] - R_mat[0, 1]),
    ], dtype=np.float64)


def so3_geodesic_distance(R1: np.ndarray, R2: np.ndarray) -> float:
    """Computes the geodesic Riemannian rotation distance ||Log(R1^T * R2)|| in radians."""
    diff_R = R1.T @ R2
    return float(np.linalg.norm(so3_log(diff_R)))
