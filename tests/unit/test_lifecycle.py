"""Unit tests for TrackLifecycleStateMachine transitions."""

import pytest
from skyvanta.core.config import LifecycleConfig
from skyvanta.core.types import TrackLifecycleState
from skyvanta.tracking.lifecycle.state_machine import TrackLifecycleStateMachine


def test_lifecycle_confirmation():
    cfg = LifecycleConfig(min_confirmed_hits=3)
    fsm = TrackLifecycleStateMachine(cfg)
    assert fsm.state == TrackLifecycleState.TENTATIVE

    # Hit 2 -> still TENTATIVE
    fsm.step(has_measurement=True)
    assert fsm.state == TrackLifecycleState.TENTATIVE

    # Hit 3 -> CONFIRMED
    fsm.step(has_measurement=True)
    assert fsm.state == TrackLifecycleState.CONFIRMED

    # Hit 4 -> TRACKING
    fsm.step(has_measurement=True)
    assert fsm.state == TrackLifecycleState.TRACKING


def test_lifecycle_coasting_and_lost():
    cfg = LifecycleConfig(min_confirmed_hits=2, max_coasting_frames=3, max_lost_frames=5)
    fsm = TrackLifecycleStateMachine(cfg)

    # Reach TRACKING
    fsm.step(has_measurement=True)
    fsm.step(has_measurement=True)
    assert fsm.state == TrackLifecycleState.TRACKING

    # Miss 1 -> COASTING
    fsm.step(has_measurement=False)
    assert fsm.state == TrackLifecycleState.COASTING

    # Miss 2 -> COASTING
    fsm.step(has_measurement=False)
    assert fsm.state == TrackLifecycleState.COASTING

    # Miss 3 -> LOST
    fsm.step(has_measurement=False)
    assert fsm.state == TrackLifecycleState.LOST

    # Recovery during LOST -> TRACKING
    fsm.step(has_measurement=True)
    assert fsm.state == TrackLifecycleState.TRACKING


def test_lifecycle_deletion():
    cfg = LifecycleConfig(min_confirmed_hits=2, max_tentative_misses=2)
    fsm = TrackLifecycleStateMachine(cfg)
    assert fsm.state == TrackLifecycleState.TENTATIVE

    # Miss 1
    fsm.step(has_measurement=False)
    assert fsm.state == TrackLifecycleState.TENTATIVE

    # Miss 2 -> DELETED
    fsm.step(has_measurement=False)
    assert fsm.state == TrackLifecycleState.DELETED


def test_lifecycle_prolonged_lost_to_deleted():
    cfg = LifecycleConfig(min_confirmed_hits=2, max_coasting_frames=2, max_lost_frames=3)
    fsm = TrackLifecycleStateMachine(cfg)
    # Confirm
    fsm.step(has_measurement=True)
    fsm.step(has_measurement=True)
    assert fsm.state == TrackLifecycleState.TRACKING

    # Coasting 2 frames
    fsm.step(has_measurement=False)
    fsm.step(has_measurement=False)
    assert fsm.state == TrackLifecycleState.LOST

    # Lost 3 frames -> DELETED
    fsm.step(has_measurement=False)
    fsm.step(has_measurement=False)
    assert fsm.state == TrackLifecycleState.DELETED


def test_lifecycle_force_delete():
    fsm = TrackLifecycleStateMachine()
    fsm.step(has_measurement=True)
    fsm.force_delete()
    assert fsm.state == TrackLifecycleState.DELETED

