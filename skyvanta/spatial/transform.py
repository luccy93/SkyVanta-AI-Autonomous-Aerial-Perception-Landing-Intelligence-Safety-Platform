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


# Constant permutation matrix mapping ENU coordinates [East, North, Up] to NED [North, East, Down]
# P_ned = R_NED_ENU @ P_enu
R_NED_ENU = np.array([
    [0.0, 1.0, 0.0],
    [1.0, 0.0, 0.0],
    [0.0, 0.0, -1.0],
], dtype=np.float64)


def enu_to_ned_position(pos_enu: np.ndarray) -> np.ndarray:
    """Converts a 3D position vector from East-North-Up (ENU) to North-East-Down (NED).

    Args:
        pos_enu: (3,) array [x_east, y_north, z_up]

    Returns:
        (3,) array [x_north, y_east, z_down]
    """
    p = np.ascontiguousarray(pos_enu, dtype=np.float64).flatten()
    return R_NED_ENU @ p


def ned_to_enu_position(pos_ned: np.ndarray) -> np.ndarray:
    """Converts a 3D position vector from North-East-Down (NED) to East-North-Up (ENU).

    Args:
        pos_ned: (3,) array [x_north, y_east, z_down]

    Returns:
        (3,) array [x_east, y_north, z_up]
    """
    p = np.ascontiguousarray(pos_ned, dtype=np.float64).flatten()
    return R_NED_ENU @ p


def enu_to_ned_velocity(vel_enu: np.ndarray) -> np.ndarray:
    """Converts a linear velocity vector from ENU (m/s) to NED (m/s)."""
    v = np.ascontiguousarray(vel_enu, dtype=np.float64).flatten()
    return R_NED_ENU @ v


def ned_to_enu_velocity(vel_ned: np.ndarray) -> np.ndarray:
    """Converts a linear velocity vector from NED (m/s) to ENU (m/s)."""
    v = np.ascontiguousarray(vel_ned, dtype=np.float64).flatten()
    return R_NED_ENU @ v


def enu_to_ned_rotation(R_enu: np.ndarray) -> np.ndarray:
    """Converts a 3x3 orientation matrix from ENU reference frame to NED reference frame."""
    R = np.ascontiguousarray(R_enu, dtype=np.float64).reshape(3, 3)
    return R_NED_ENU @ R @ R_NED_ENU


def ned_to_enu_rotation(R_ned: np.ndarray) -> np.ndarray:
    """Converts a 3x3 orientation matrix from NED reference frame to ENU reference frame."""
    R = np.ascontiguousarray(R_ned, dtype=np.float64).reshape(3, 3)
    return R_NED_ENU @ R @ R_NED_ENU

