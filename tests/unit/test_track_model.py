"""Unit tests for Track and TrajectoryPoint data models."""

import pytest
from skyvanta.core.types import BoundingBox, DetectionSource, Track, TrackLifecycleState, TrajectoryPoint


def test_trajectory_point_model():
    pt = TrajectoryPoint(
        x=150.0,
        y=200.0,
        w=40.0,
        h=30.0,
        timestamp_sec=1.25,
        confidence=0.9,
        state=TrackLifecycleState.TRACKING,
    )
    assert pt.x == 150.0
    assert pt.y == 200.0
    assert pt.w == 40.0
    assert pt.h == 30.0
    assert pt.timestamp_sec == 1.25
    assert pt.state == TrackLifecycleState.TRACKING


def test_track_model():
    box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    trk = Track(
        track_id=1,
        state=TrackLifecycleState.TENTATIVE,
        bbox=box,
        confidence=0.85,
        track_quality=0.75,
        age=1,
        hits=1,
        consecutive_hits=1,
        missed_frames=0,
        velocity_px_per_sec=(10.0, -5.0),
        source_class="drone",
        source=DetectionSource.YOLO,
    )
    assert trk.track_id == 1
    assert trk.state == TrackLifecycleState.TENTATIVE
    assert trk.bbox.width == 100.0
    assert trk.velocity_px_per_sec == (10.0, -5.0)
    assert trk.track_quality == 0.75

    # Test serialization round-trip
    dumped = trk.model_dump()
    assert dumped["track_id"] == 1
    assert dumped["state"] == "TENTATIVE"
    
    json_str = trk.model_dump_json()
    assert "track_id" in json_str
    
    restored = Track.model_validate_json(json_str)
    assert restored.track_id == trk.track_id
    assert restored.state == trk.state
    assert restored.bbox.x1 == trk.bbox.x1


def test_track_state_enum_values():
    assert TrackLifecycleState.TENTATIVE.value == "TENTATIVE"
    assert TrackLifecycleState.CONFIRMED.value == "CONFIRMED"
    assert TrackLifecycleState.TRACKING.value == "TRACKING"
    assert TrackLifecycleState.COASTING.value == "COASTING"
    assert TrackLifecycleState.LOST.value == "LOST"
    assert TrackLifecycleState.DELETED.value == "DELETED"

