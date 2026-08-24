"""Unit tests for spatial rotation transforms and representations."""

import math
import pytest
import numpy as np

from skyvanta.spatial.transform import (
    euler_to_rotation_matrix,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_euler,
    rotation_matrix_to_quaternion,
    rotation_matrix_to_rvec,
    rvec_to_rotation_matrix,
)


def test_rodrigues_roundtrip():
    rvec_orig = np.array([0.1, -0.2, 0.3], dtype=np.float64)
    R = rvec_to_rotation_matrix(rvec_orig)
    assert R.shape == (3, 3)
    # Check orthonormality R * R^T = I
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-6)

    rvec_rec = rotation_matrix_to_rvec(R)
    assert np.allclose(rvec_orig, rvec_rec, atol=1e-6)


def test_quaternion_roundtrip():
    # 45-degree rotation around Y axis
    theta = math.radians(45.0)
    q_orig = (math.cos(theta / 2.0), 0.0, math.sin(theta / 2.0), 0.0)

    R = quaternion_to_rotation_matrix(q_orig)
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-6)

    q_rec = rotation_matrix_to_quaternion(R)
    assert np.allclose(q_orig, q_rec, atol=1e-6)


def test_euler_roundtrip():
    roll_deg, pitch_deg, yaw_deg = 10.0, -20.0, 30.0
    roll_rad, pitch_rad, yaw_rad = math.radians(roll_deg), math.radians(pitch_deg), math.radians(yaw_deg)

    R = euler_to_rotation_matrix(roll_rad, pitch_rad, yaw_rad)
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-6)

    (r_rad, p_rad, y_rad), (r_deg, p_deg, y_deg) = rotation_matrix_to_euler(R)
    assert pytest.approx(r_deg, abs=1e-4) == roll_deg
    assert pytest.approx(p_deg, abs=1e-4) == pitch_deg
    assert pytest.approx(y_deg, abs=1e-4) == yaw_deg
