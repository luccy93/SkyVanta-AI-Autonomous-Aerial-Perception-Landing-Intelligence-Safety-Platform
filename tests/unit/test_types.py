"""Unit tests for SkyVanta core data types and geometric calculations."""

import pytest
from skyvanta.core.types import BoundingBox, Detection, TrackState, TelemetryEstimate


def test_bounding_box_properties():
    box = BoundingBox(x1=50.0, y1=60.0, x2=150.0, y2=160.0)
    assert box.width == 100.0
    assert box.height == 100.0
    assert box.center == (100.0, 110.0)
    assert box.area == 10000.0
    assert box.to_tuple() == (50.0, 60.0, 150.0, 160.0)


def test_bounding_box_iou():
    box1 = BoundingBox(x1=0.0, y1=0.0, x2=10.0, y2=10.0)
    box2 = BoundingBox(x1=5.0, y1=0.0, x2=15.0, y2=10.0)
    # intersection: 5 * 10 = 50
    # union: 100 + 100 - 50 = 150
    # iou: 50 / 150 = 1/3
    assert pytest.approx(box1.iou(box2), rel=1e-3) == 1.0 / 3.0


def test_bounding_box_no_overlap():
    box1 = BoundingBox(x1=0.0, y1=0.0, x2=10.0, y2=10.0)
    box2 = BoundingBox(x1=20.0, y1=20.0, x2=30.0, y2=30.0)
    assert box1.iou(box2) == 0.0


def test_detection_model():
    box = BoundingBox(x1=10.0, y1=10.0, x2=20.0, y2=20.0)
    det = Detection(bbox=box, confidence=0.85, class_name="drone", source="yolo")
    assert det.confidence == 0.85
    assert det.source == "yolo"


def test_track_state_enum():
    assert TrackState.SEARCHING.value == "SEARCHING"
    assert TrackState.LOCKED.value == "LOCKED"
