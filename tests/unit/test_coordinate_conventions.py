"""Unit tests for H3-04: Coordinate frame metadata consistency and ENU/NED conversions."""

import numpy as np
import pytest
from skyvanta.core.types import FrameId
from skyvanta.spatial.frames import STANDARD_FRAMES
from skyvanta.spatial.transform import (
    enu_to_ned_position,
    ned_to_enu_position,
    enu_to_ned_velocity,
    ned_to_enu_velocity,
    enu_to_ned_rotation,
    ned_to_enu_rotation,
    euler_to_rotation_matrix,
)


def test_world_frame_definition_is_enu():
    """Verifies that FrameId.WORLD formally declares ENU convention and valid descriptions."""
    world_frame = STANDARD_FRAMES[FrameId.WORLD]
    assert world_frame.convention == "ENU"
    assert world_frame.is_inertial is True
    assert "+X: East" in world_frame.axes_description
    assert "+Y: North" in world_frame.axes_description
    assert "+Z: Up" in world_frame.axes_description


def test_enu_to_ned_position_conversion():
    """Verifies position mapping: East -> Y_ned, North -> X_ned, Up -> -Z_ned."""
    # 10m East, 20m North, 5m Up (altitude)
    p_enu = np.array([10.0, 20.0, 5.0])
    p_ned = enu_to_ned_position(p_enu)

    # In NED: X=North (20), Y=East (10), Z=Down (-5)
    np.testing.assert_allclose(p_ned, [20.0, 10.0, -5.0])

    # Round trip
    p_roundtrip = ned_to_enu_position(p_ned)
    np.testing.assert_allclose(p_roundtrip, p_enu)


def test_enu_to_ned_velocity_conversion():
    """Verifies velocity mapping: positive upward climb becomes negative down rate."""
    v_enu = np.array([1.5, -2.0, 0.8])  # 0.8 m/s climb
    v_ned = enu_to_ned_velocity(v_enu)

    np.testing.assert_allclose(v_ned, [-2.0, 1.5, -0.8])

    v_roundtrip = ned_to_enu_velocity(v_ned)
    np.testing.assert_allclose(v_roundtrip, v_enu)


def test_enu_to_ned_rotation_matrix_roundtrip():
    """Verifies rotation transform orthonormality and roundtrip consistency."""
    R_enu = euler_to_rotation_matrix(np.radians(10.0), np.radians(-15.0), np.radians(45.0))
    R_ned = enu_to_ned_rotation(R_enu)

    # Check orthonormality in NED
    np.testing.assert_allclose(R_ned.T @ R_ned, np.eye(3), atol=1e-10)

    # Check roundtrip
    R_roundtrip = ned_to_enu_rotation(R_ned)
    np.testing.assert_allclose(R_roundtrip, R_enu, atol=1e-10)
