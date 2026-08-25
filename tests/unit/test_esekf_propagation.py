"""Unit tests for 15-state ESEKF propagation and covariance evolution."""

import math
import numpy as np
import pytest

from skyvanta.core.config import IMUNoiseConfig
from skyvanta.core.types import FilterStatus
from skyvanta.fusion.imu import GravityModel
from skyvanta.fusion.propagation import StatePropagator
from skyvanta.fusion.state import ESEKFState, STATE_DIM


def test_stationary_hover_gravity_reaction_propagation():
    """Verifies that an accelerometer measuring specific force reaction (0, 0, -g) perfectly cancels gravity."""
    propagator = StatePropagator()

    initial_state = ESEKFState(
        position=(0.0, 0.0, -10.0),
        velocity=(0.0, 0.0, 0.0),
        rotation_matrix=np.eye(3),
        gyro_bias=(0.0, 0.0, 0.0),
        accel_bias=(0.0, 0.0, 0.0),
        status=FilterStatus.INITIALIZED,
    )

    # Accelerometer measures reaction force upward in body frame (-9.80665)
    w_m = np.array([0.0, 0.0, 0.0])
    a_m = np.array([0.0, 0.0, -9.80665])
    dt = 0.01

    state = initial_state
    for i in range(100):
        state = propagator.propagate(state, w_m, a_m, dt, timestamp_sec=float(i * dt))

    # Position and velocity must remain exactly stationary
    np.testing.assert_allclose(state.p, [0.0, 0.0, -10.0], atol=1e-5)
    np.testing.assert_allclose(state.v, [0.0, 0.0, 0.0], atol=1e-5)
    np.testing.assert_allclose(state.R, np.eye(3), atol=1e-5)


def test_constant_acceleration_propagation():
    """Verifies kinematic velocity and position integration under constant forward body acceleration."""
    propagator = StatePropagator()

    initial_state = ESEKFState(
        position=(0.0, 0.0, 0.0),
        velocity=(0.0, 0.0, 0.0),
        rotation_matrix=np.eye(3),
    )

    # Accelerometer measures +1.0 m/s^2 forward (+X) along with -g reaction in Z
    w_m = np.array([0.0, 0.0, 0.0])
    a_m = np.array([1.0, 0.0, -9.80665])
    dt = 0.01

    state = initial_state
    for i in range(100):  # 1.0 second total
        state = propagator.propagate(state, w_m, a_m, dt, timestamp_sec=float((i + 1) * dt))

    # Expected: v = 1.0 m/s, p = 0.5 * 1.0 * (1.0)^2 = 0.5 m
    np.testing.assert_allclose(state.v, [1.0, 0.0, 0.0], atol=1e-3)
    np.testing.assert_allclose(state.p, [0.5, 0.0, 0.0], atol=1e-3)


def test_covariance_symmetry_and_growth_during_propagation():
    """Verifies that error covariance P grows monotonically with IMU noise and preserves symmetry."""
    propagator = StatePropagator()

    initial_P = np.eye(STATE_DIM) * 0.1
    initial_state = ESEKFState(covariance=initial_P)

    w_m = np.array([0.0, 0.0, 0.0])
    a_m = np.array([0.0, 0.0, -9.80665])
    dt = 0.01

    state = propagator.propagate(initial_state, w_m, a_m, dt, timestamp_sec=0.01)

    # Symmetry check: P = P^T
    np.testing.assert_allclose(state.P, state.P.T, atol=1e-12)

    # Growth check: trace(P_next) > trace(P_init)
    assert np.trace(state.P) > np.trace(initial_P)

    # Positive definiteness check (all eigenvalues > 0)
    eigenvalues = np.linalg.eigvals(state.P)
    assert np.all(eigenvalues > 0)
