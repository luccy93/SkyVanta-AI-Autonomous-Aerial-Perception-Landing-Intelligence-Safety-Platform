"""Spatial coordinate transformations, rotation representations, and frame conversions."""

import math
from typing import Tuple
import cv2
import numpy as np


def rvec_to_rotation_matrix(rvec: np.ndarray) -> np.ndarray:
    """Converts a Rodrigues rotation vector (3,) or (3, 1) to a 3x3 orthonormal rotation matrix."""
    r = np.ascontiguousarray(rvec, dtype=np.float64).reshape(3, 1)
    R, _ = cv2.Rodrigues(r)
    return R


def rotation_matrix_to_rvec(R: np.ndarray) -> np.ndarray:
    """Converts a 3x3 orthonormal rotation matrix to a Rodrigues rotation vector (3,)."""
    R_mat = np.ascontiguousarray(R, dtype=np.float64).reshape(3, 3)
    rvec, _ = cv2.Rodrigues(R_mat)
    return rvec.flatten()


def rotation_matrix_to_quaternion(R: np.ndarray) -> Tuple[float, float, float, float]:
    """Converts a 3x3 orthonormal rotation matrix to a normalized unit quaternion (qw, qx, qy, qz)."""
    R_mat = np.ascontiguousarray(R, dtype=np.float64).reshape(3, 3)
    tr = np.trace(R_mat)

    if tr > 0.0:
        S = math.sqrt(tr + 1.0) * 2.0
        qw = 0.25 * S
        qx = (R_mat[2, 1] - R_mat[1, 2]) / S
        qy = (R_mat[0, 2] - R_mat[2, 0]) / S
        qz = (R_mat[1, 0] - R_mat[0, 1]) / S
    elif (R_mat[0, 0] > R_mat[1, 1]) and (R_mat[0, 0] > R_mat[2, 2]):
        S = math.sqrt(1.0 + R_mat[0, 0] - R_mat[1, 1] - R_mat[2, 2]) * 2.0
        qw = (R_mat[2, 1] - R_mat[1, 2]) / S
        qx = 0.25 * S
        qy = (R_mat[0, 1] + R_mat[1, 0]) / S
        qz = (R_mat[0, 2] + R_mat[2, 0]) / S
    elif R_mat[1, 1] > R_mat[2, 2]:
        S = math.sqrt(1.0 + R_mat[1, 1] - R_mat[0, 0] - R_mat[2, 2]) * 2.0
        qw = (R_mat[0, 2] - R_mat[2, 0]) / S
        qx = (R_mat[0, 1] + R_mat[1, 0]) / S
        qy = 0.25 * S
        qz = (R_mat[1, 2] + R_mat[2, 1]) / S
    else:
        S = math.sqrt(1.0 + R_mat[2, 2] - R_mat[0, 0] - R_mat[1, 1]) * 2.0
        qw = (R_mat[1, 0] - R_mat[0, 1]) / S
        qx = (R_mat[0, 2] + R_mat[2, 0]) / S
        qy = (R_mat[1, 2] + R_mat[2, 1]) / S
        qz = 0.25 * S

    norm = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    if norm > 0.0:
        return (qw / norm, qx / norm, qy / norm, qz / norm)
    return (1.0, 0.0, 0.0, 0.0)


def quaternion_to_rotation_matrix(q: Tuple[float, float, float, float]) -> np.ndarray:
    """Converts a unit quaternion (qw, qx, qy, qz) to a 3x3 orthonormal rotation matrix."""
    qw, qx, qy, qz = q
    norm = math.sqrt(qw * qw + qx * qx + qy * qy + qz * qz)
    if norm > 0:
        qw, qx, qy, qz = qw / norm, qx / norm, qy / norm, qz / norm

    R = np.array([
        [1.0 - 2.0 * (qy * qy + qz * qz), 2.0 * (qx * qy - qz * qw), 2.0 * (qx * qz + qy * qw)],
        [2.0 * (qx * qy + qz * qw), 1.0 - 2.0 * (qx * qx + qz * qz), 2.0 * (qy * qz - qx * qw)],
        [2.0 * (qx * qz - qy * qw), 2.0 * (qy * qz + qx * qw), 1.0 - 2.0 * (qx * qx + qy * qy)],
    ], dtype=np.float64)
    return R


def rotation_matrix_to_euler(R: np.ndarray) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """Extracts Tait-Bryan Euler angles (roll, pitch, yaw) in standard Z-Y-X sequence.

    Returns:
        ((roll_rad, pitch_rad, yaw_rad), (roll_deg, pitch_deg, yaw_deg))
    """
    R_mat = np.ascontiguousarray(R, dtype=np.float64).reshape(3, 3)
    sy = math.sqrt(R_mat[0, 0] * R_mat[0, 0] + R_mat[1, 0] * R_mat[1, 0])

    singular = sy < 1e-6

    if not singular:
        roll = math.atan2(R_mat[2, 1], R_mat[2, 2])
        pitch = math.atan2(-R_mat[2, 0], sy)
        yaw = math.atan2(R_mat[1, 0], R_mat[0, 0])
    else:
        roll = math.atan2(-R_mat[1, 2], R_mat[1, 1])
        pitch = math.atan2(-R_mat[2, 0], sy)
        yaw = 0.0

    rad = (float(roll), float(pitch), float(yaw))
    deg = (math.degrees(roll), math.degrees(pitch), math.degrees(yaw))
    return rad, deg


def euler_to_rotation_matrix(roll_rad: float, pitch_rad: float, yaw_rad: float) -> np.ndarray:
    """Constructs a 3x3 orthonormal rotation matrix from Tait-Bryan Euler angles (roll, pitch, yaw) in radians."""
    Rx = np.array([
        [1.0, 0.0, 0.0],
        [0.0, math.cos(roll_rad), -math.sin(roll_rad)],
        [0.0, math.sin(roll_rad), math.cos(roll_rad)],
    ], dtype=np.float64)

    Ry = np.array([
        [math.cos(pitch_rad), 0.0, math.sin(pitch_rad)],
        [0.0, 1.0, 0.0],
        [-math.sin(pitch_rad), 0.0, math.cos(pitch_rad)],
    ], dtype=np.float64)

    Rz = np.array([
        [math.cos(yaw_rad), -math.sin(yaw_rad), 0.0],
        [math.sin(yaw_rad), math.cos(yaw_rad), 0.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)

    return Rz @ Ry @ Rx
