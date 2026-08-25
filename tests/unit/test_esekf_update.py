"""Unit tests for visual pose measurement update, innovation gating, and covariance reset."""

import math
import numpy as np
import pytest

from skyvanta.core.config import ESEKFConfig
from skyvanta.core.types import FilterStatus, FrameId, VisualPoseMeasurement
from skyvanta.fusion.so3 import so3_exp
from skyvanta.fusion.state import ESEKFState, STATE_DIM
from skyvanta.fusion.update import KalmanUpdater
from skyvanta.spatial.transform import rotation_matrix_to_quaternion


def test_visual_pose_position_correction():
    """Verifies that visual pose observation corrects nominal position error and reduces covariance."""
    updater = KalmanUpdater()

    # Prior state has position offset (1.0, 0.0, 0.0) with large variance
    initial_P = np.eye(STATE_DIM) * 2.0
    prior_state = ESEKFState(
        position=(1.0, 0.0, 0.0),
        velocity=(0.0, 0.0, 0.0),
        rotation_matrix=np.eye(3),
        covariance=initial_P,
        status=FilterStatus.INITIALIZED,
    )

    # Observation at true position (0.0, 0.0, 0.0)
    meas = VisualPoseMeasurement(
        timestamp_sec=1.0,
        position_m=(0.0, 0.0, 0.0),
        rotation_matrix=np.eye(3).tolist(),
        quaternion=(1.0, 0.0, 0.0, 0.0),
        frame_id=FrameId.WORLD,
        quality=1.0,
    )

    updated_state, nis, accepted, reason = updater.update(prior_state, meas)

    assert accepted is True
    assert reason is None
    # Position estimate should be pulled towards 0.0
    assert updated_state.p[0] < 0.5
    # Covariance should decrease
    assert np.trace(updated_state.P) < np.trace(initial_P)
    # Symmetry preserved
    np.testing.assert_allclose(updated_state.P, updated_state.P.T, atol=1e-10)


def test_visual_pose_orientation_correction():
    """Verifies that visual pose observation corrects orientation drift on SO(3)."""
    updater = KalmanUpdater()

    # Prior state has 10-degree yaw drift
    R_drift = so3_exp(np.array([0.0, 0.0, math.radians(10.0)]))
    prior_state = ESEKFState(
        position=(0.0, 0.0, 0.0),
        rotation_matrix=R_drift,
        covariance=np.eye(STATE_DIM) * 1.0,
        status=FilterStatus.INITIALIZED,
    )

    # Observation with true identity rotation
    meas = VisualPoseMeasurement(
        timestamp_sec=1.0,
        position_m=(0.0, 0.0, 0.0),
        rotation_matrix=np.eye(3).tolist(),
        quaternion=(1.0, 0.0, 0.0, 0.0),
    )

    updated_state, nis, accepted, reason = updater.update(prior_state, meas)
    assert accepted is True

    # Corrected orientation must be closer to identity than R_drift
    angle_drift = np.linalg.norm(np.array([0.0, 0.0, math.radians(10.0)]))
    angle_updated = np.linalg.norm(updated_state.R - np.eye(3))
    assert angle_updated < angle_drift


def test_outlier_rejection_via_chi2_gating():
    """Verifies that severe visual outliers are rejected and state is unchanged."""
    cfg = ESEKFConfig(gating_threshold_chi2=16.81)
    updater = KalmanUpdater(cfg)

    prior_state = ESEKFState(
        position=(0.0, 0.0, 0.0),
        rotation_matrix=np.eye(3),
        covariance=np.eye(STATE_DIM) * 0.1,  # tight uncertainty
        status=FilterStatus.INITIALIZED,
    )

    # Outlier position (50m jump)
    outlier_meas = VisualPoseMeasurement(
        timestamp_sec=1.0,
        position_m=(50.0, -40.0, 30.0),
        rotation_matrix=np.eye(3).tolist(),
        quaternion=(1.0, 0.0, 0.0, 0.0),
    )

    updated_state, nis, accepted, reason = updater.update(prior_state, outlier_meas)

    assert accepted is False
    assert "exceeds Chi-squared gate" in str(reason)
    # State must be completely unmodified
    np.testing.assert_allclose(updated_state.p, prior_state.p, atol=1e-12)
    np.testing.assert_allclose(updated_state.P, prior_state.P, atol=1e-12)
