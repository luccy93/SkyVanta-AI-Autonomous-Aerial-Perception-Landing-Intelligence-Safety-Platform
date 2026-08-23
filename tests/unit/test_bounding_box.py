"""Comprehensive unit tests for BoundingBox operations and edge cases."""

import math
import pytest
from skyvanta.core.types import BoundingBox


def test_bounding_box_construction():
    box = BoundingBox(x1=10.0, y1=20.0, x2=110.0, y2=120.0)
    assert box.x1 == 10.0
    assert box.y1 == 20.0
    assert box.x2 == 110.0
    assert box.y2 == 120.0
    assert box.width == 100.0
    assert box.height == 100.0
    assert box.center == (60.0, 70.0)
    assert box.area == 10000.0
    assert box.aspect_ratio == 1.0
    assert box.to_tuple() == (10.0, 20.0, 110.0, 120.0)
    assert box.to_int_tuple() == (10, 20, 110, 120)


def test_bounding_box_is_valid():
    valid_box = BoundingBox(x1=10.0, y1=10.0, x2=50.0, y2=50.0)
    assert valid_box.is_valid() is True

    # Inverted coordinates
    inverted_x = BoundingBox(x1=50.0, y1=10.0, x2=10.0, y2=50.0)
    assert inverted_x.is_valid() is False

    # Zero size box
    zero_box = BoundingBox(x1=10.0, y1=10.0, x2=10.0, y2=10.0)
    assert zero_box.is_valid() is False
    assert zero_box.is_valid(min_size=0.0) is False

    # NaN / Inf coordinates
    nan_box = BoundingBox(x1=float('nan'), y1=10.0, x2=50.0, y2=50.0)
    assert nan_box.is_valid() is False

    inf_box = BoundingBox(x1=10.0, y1=float('inf'), x2=50.0, y2=50.0)
    assert inf_box.is_valid() is False


def test_bounding_box_clipping():
    box = BoundingBox(x1=-20.0, y1=-10.0, x2=1300.0, y2=800.0)
    clipped = box.clip(max_width=1280.0, max_height=720.0)
    assert clipped.x1 == 0.0
    assert clipped.y1 == 0.0
    assert clipped.x2 == 1280.0
    assert clipped.y2 == 720.0
    assert clipped.width == 1280.0
    assert clipped.height == 720.0


def test_bounding_box_iou_cases():
    box_a = BoundingBox(x1=0.0, y1=0.0, x2=100.0, y2=100.0)
    box_b = BoundingBox(x1=0.0, y1=0.0, x2=100.0, y2=100.0)
    # Identical boxes
    assert pytest.approx(box_a.iou(box_b)) == 1.0

    # 50% horizontal overlap
    box_c = BoundingBox(x1=50.0, y1=0.0, x2=150.0, y2=100.0)
    # intersection: 50 * 100 = 5000
    # union: 10000 + 10000 - 5000 = 15000
    assert pytest.approx(box_a.iou(box_c)) == 1.0 / 3.0

    # Non-overlapping
    box_d = BoundingBox(x1=200.0, y1=200.0, x2=300.0, y2=300.0)
    assert box_a.iou(box_d) == 0.0

    # Touching boundary only
    box_e = BoundingBox(x1=100.0, y1=0.0, x2=200.0, y2=100.0)
    assert box_a.iou(box_e) == 0.0

    # Invalid box IoU returns 0.0
    invalid_box = BoundingBox(x1=10.0, y1=10.0, x2=5.0, y2=5.0)
    assert box_a.iou(invalid_box) == 0.0
