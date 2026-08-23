"""Unit tests for OneEuroFilter and Vec2EuroFilter jitter filters."""

import pytest
from skyvanta.tracking.smoothing import OneEuroFilter, Vec2EuroFilter


def test_one_euro_filter_initialization():
    f = OneEuroFilter(freq=30.0, min_cutoff=1.0, beta=0.01)
    val = f(100.0, t=0.0)
    assert val == 100.0


def test_one_euro_filter_smoothing():
    f = OneEuroFilter(freq=30.0, min_cutoff=0.5, beta=0.001)
    # Apply jump with noise
    f(0.0, t=0.0)
    smooth_val = f(10.0, t=1.0 / 30.0)
    # Filtered value should be between 0 and 10
    assert 0.0 < smooth_val < 10.0


def test_vec2_euro_filter():
    f = Vec2EuroFilter(min_cutoff=1.0, beta=0.01)
    pt = f((50.0, 60.0), t=0.0)
    assert pt == (50.0, 60.0)
    next_pt = f((55.0, 65.0), t=1.0 / 30.0)
    assert 50.0 < next_pt[0] < 55.0
    assert 60.0 < next_pt[1] < 65.0
