"""Unit tests for EnvironmentalConditions and LandingPadModel."""

import numpy as np
import pytest

from skyvanta.simulation.environment import EnvironmentalConditions, LandingPadModel


def test_environmental_conditions_wind():
    """Verifies baseline wind and gust calculations."""
    env = EnvironmentalConditions(base_wind_mps=(2.0, 0.0, 0.0), gust_amplitude_mps=1.0)
    w0 = env.get_wind_at(0.0)
    assert w0.shape == (3,)
    assert pytest.approx(w0[0], abs=0.5) == 2.0


def test_landing_pad_model_static():
    """Verifies 3D corner generation for static landing pad."""
    pad = LandingPadModel(initial_position=(0.0, 0.0, 0.0), marker_size_m=0.20)
    corners = pad.get_3d_corners(0.0)
    assert corners.shape == (4, 3)
    # Side length should be 0.20m
    side = np.linalg.norm(corners[0] - corners[1])
    assert pytest.approx(side, rel=1e-3) == 0.20


def test_landing_pad_model_moving():
    """Verifies position propagation for moving pad."""
    pad = LandingPadModel(initial_position=(0.0, 0.0, 0.0), velocity_mps=(1.0, 0.0, 0.0))
    pos_5s = pad.get_position_at(5.0)
    assert pytest.approx(pos_5s[0], rel=1e-3) == 5.0
