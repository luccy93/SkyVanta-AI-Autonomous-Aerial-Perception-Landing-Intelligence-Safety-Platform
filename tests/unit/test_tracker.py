"""Unit tests for DroneTracker and TrackStateMachine."""

import pytest
import numpy as np
from skyvanta.core.types import TrackState
from skyvanta.core.config import SkyVantaConfig
from skyvanta.tracking.state import TrackStateMachine
from skyvanta.tracking.tracker import DroneTracker


def test_track_state_machine_transitions():
    fsm = TrackStateMachine()
    assert fsm.state == TrackState.SEARCHING

    # Step up transitions
    fsm.update(confidence=0.30, frames_since_hit=0)
    assert fsm.state == TrackState.ACQUIRED

    fsm.update(confidence=0.50, frames_since_hit=0)
    assert fsm.state == TrackState.TRACKING

    fsm.update(confidence=0.75, frames_since_hit=0)
    assert fsm.state == TrackState.LOCKED

    fsm.update(confidence=0.90, frames_since_hit=0)
    assert fsm.state == TrackState.APPROACHING


def test_drone_tracker_initial_state():
    config = SkyVantaConfig()
    config.detector.use_yolo = False
    tracker = DroneTracker((720, 1280), config=config)

    assert tracker.state == TrackState.SEARCHING
    assert tracker.hits == 0
    assert not tracker.is_visible


def test_drone_tracker_update_black_frame():
    config = SkyVantaConfig()
    config.detector.use_yolo = False
    tracker = DroneTracker((720, 1280), config=config)

    black_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    box, conf, state = tracker.update(black_frame, t_sec=0.0)

    assert state == TrackState.SEARCHING
    assert conf == 0.0
