"""Unit tests for 15-state ESEKF data models and state representations."""

import numpy as np
import pytest

from skyvanta.core.types import FilterStatus, FrameId, NominalState
from skyvanta.fusion.state import (
    ESEKFState,
    INDEX_ATT,
    INDEX_BA,
    INDEX_BG,
    INDEX_POS,
    INDEX_VEL,
    STATE_DIM,
)


def test_esekf_state_dimension_and_indices():
    """Verifies that the error-state vector has exactly 15 dimensions with correct slice indices."""
    assert STATE_DIM == 15
    assert INDEX_POS == slice(0, 3)
    assert INDEX_VEL == slice(3, 6)
    assert INDEX_ATT == slice(6, 9)
    assert INDEX_BG == slice(9, 12)
    assert INDEX_BA == slice(12, 15)


def test_esekf_state_nominal_export():
    """Verifies conversion from mathematical ESEKFState to strongly-typed NominalState."""
    state = ESEKFState(
        position=(1.5, -2.0, -10.0),
        velocity=(0.5, 0.0, -0.2),
        gyro_bias=(0.001, -0.002, 0.0),
        accel_bias=(0.01, 0.02, -0.03),
        timestamp_sec=12.5,
        status=FilterStatus.INITIALIZED,
    )

    nominal = state.to_nominal_state()
    assert isinstance(nominal, NominalState)
    assert nominal.position_world == (1.5, -2.0, -10.0)
    assert nominal.velocity_world == (0.5, 0.0, -0.2)
    assert nominal.gyro_bias == (0.001, -0.002, 0.0)
    assert nominal.accel_bias == (0.01, 0.02, -0.03)
    assert nominal.timestamp_sec == 12.5
    assert nominal.status == FilterStatus.INITIALIZED
    assert nominal.frame_id == FrameId.WORLD
