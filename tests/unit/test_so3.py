"""Unit tests for Lie Group SO(3) and Lie Algebra so(3) mathematical operations."""

import math
import numpy as np
import pytest

from skyvanta.fusion.so3 import skew_symmetric, so3_exp, so3_geodesic_distance, so3_log


def test_skew_symmetric():
    """Verifies anti-symmetry of the skew-symmetric matrix operator."""
    v = np.array([1.0, -2.0, 3.5])
    K = skew_symmetric(v)

    # K^T = -K
    np.testing.assert_allclose(K.T, -K, atol=1e-12)
    # Diagonal is zero
    np.testing.assert_allclose(np.diag(K), np.zeros(3), atol=1e-12)


def test_so3_exp_identity():
    """Verifies Exp(0) yields 3x3 identity matrix."""
    v_zero = np.zeros(3)
    R = so3_exp(v_zero)
    np.testing.assert_allclose(R, np.eye(3), atol=1e-12)


def test_so3_exp_small_angle():
    """Verifies smooth small-angle behavior without division-by-zero singularities."""
    v_small = np.array([1e-8, -2e-8, 1.5e-8])
    R = so3_exp(v_small)

    # Check SO(3) orthonormality
    np.testing.assert_allclose(R.T @ R, np.eye(3), atol=1e-12)
    np.testing.assert_allclose(np.linalg.det(R), 1.0, atol=1e-12)


def test_so3_exp_and_log_roundtrip():
    """Verifies Log(Exp(v)) == v for arbitrary rotations."""
    test_vectors = [
        np.array([0.1, -0.2, 0.3]),
        np.array([0.0, math.pi / 2, 0.0]),
        np.array([math.pi / 4, -math.pi / 4, math.pi / 3]),
        np.array([1e-7, 2e-7, -3e-7]),
    ]

    for v in test_vectors:
        R = so3_exp(v)
        # Check orthonormality
        np.testing.assert_allclose(R.T @ R, np.eye(3), atol=1e-10)
        np.testing.assert_allclose(np.linalg.det(R), 1.0, atol=1e-10)

        v_recovered = so3_log(R)
        np.testing.assert_allclose(v_recovered, v, atol=1e-9)


def test_so3_geodesic_distance():
    """Verifies geodesic metric distance on SO(3)."""
    R1 = np.eye(3)
    R2 = so3_exp(np.array([0.0, 0.0, math.radians(45.0)]))

    dist = so3_geodesic_distance(R1, R2)
    assert pytest.approx(math.degrees(dist), rel=1e-4) == 45.0
