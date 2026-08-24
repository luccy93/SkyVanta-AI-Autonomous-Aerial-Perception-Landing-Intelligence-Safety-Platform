"""Unit tests for TrajectoryHistory and velocity estimation."""

import pytest
from skyvanta.core.config import TrajectoryConfig
from skyvanta.core.types import BoundingBox, TrackLifecycleState
from skyvanta.tracking.trajectory.history import TrajectoryHistory


def test_trajectory_bounded_history():
    cfg = TrajectoryConfig(max_history_length=5)
    hist = TrajectoryHistory(cfg)

    for i in range(10):
        box = BoundingBox(x1=i * 10, y1=i * 10, x2=i * 10 + 20, y2=i * 10 + 20)
        hist.append(box, timestamp_sec=i * 0.1, state=TrackLifecycleState.TRACKING)

    pts = hist.get_points()
    # Memory must be bounded to max_history_length
    assert len(pts) == 5
    # Most recent point should be frame 9
    assert pts[-1].x == 90.0 + 10.0


def test_trajectory_velocity_estimation():
    cfg = TrajectoryConfig(max_history_length=20, velocity_smoothing_alpha=1.0)
    hist = TrajectoryHistory(cfg)

    # Move at 100 pixels / sec along x
    box0 = BoundingBox(x1=0, y1=0, x2=20, y2=20)
    hist.append(box0, timestamp_sec=0.0)

    box1 = BoundingBox(x1=10, y1=0, x2=30, y2=20)
    hist.append(box1, timestamp_sec=0.1)  # 10px / 0.1s = 100 px/s

    vx, vy = hist.current_velocity_px_per_sec
    assert pytest.approx(vx, abs=1.0) == 100.0
    assert pytest.approx(vy, abs=1.0) == 0.0


def test_trajectory_scale_expansion_and_clear():
    hist = TrajectoryHistory()
    # Expanding box size over 10 frames
    for i in range(10):
        size = 20.0 + i * 5.0
        box = BoundingBox(x1=100.0, y1=100.0, x2=100.0 + size, y2=100.0 + size)
        hist.append(box, timestamp_sec=i * 0.033)

    expansion = hist.scale_expansion_rate()
    assert expansion > 0.0  # Expanding target indicates approach

    hist.clear()
    assert len(hist.get_points()) == 0
    assert hist.current_velocity_px_per_sec == (0.0, 0.0)

