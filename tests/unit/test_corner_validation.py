"""Unit tests for planar corner validation and geometry checks."""

import pytest
import numpy as np

from skyvanta.target.validation import CornerValidator


def test_valid_convex_corners():
    validator = CornerValidator(min_area_px=20.0)
    # Square corners in standard CW or CCW order
    corners = np.array([
        [100.0, 100.0],
        [200.0, 100.0],
        [200.0, 200.0],
        [100.0, 200.0],
    ])
    is_valid, err = validator.validate(corners)
    assert is_valid is True
    assert err is None


def test_invalid_corner_count():
    validator = CornerValidator()
    corners_3 = np.array([[100.0, 100.0], [200.0, 100.0], [200.0, 200.0]])
    is_valid, err = validator.validate(corners_3)
    assert is_valid is False
    assert "Expected exactly 4 corners" in err


def test_non_finite_corners():
    validator = CornerValidator()
    corners_nan = np.array([
        [100.0, 100.0],
        [float("nan"), 100.0],
        [200.0, 200.0],
        [100.0, 200.0],
    ])
    is_valid, err = validator.validate(corners_nan)
    assert is_valid is False
    assert "non-finite" in err


def test_duplicate_corners():
    validator = CornerValidator()
    corners_dup = np.array([
        [100.0, 100.0],
        [100.0, 100.0],  # Duplicate
        [200.0, 200.0],
        [100.0, 200.0],
    ])
    is_valid, err = validator.validate(corners_dup)
    assert is_valid is False
    assert "Duplicate or overlapping" in err


def test_insufficient_area():
    validator = CornerValidator(min_area_px=100.0)
    # Tiny 2x2 box (area 4 px²)
    corners_tiny = np.array([
        [100.0, 100.0],
        [102.0, 100.0],
        [102.0, 102.0],
        [100.0, 102.0],
    ])
    is_valid, err = validator.validate(corners_tiny)
    assert is_valid is False
    assert "below minimum threshold" in err


def test_concave_self_intersecting_corners():
    validator = CornerValidator()
    # Dart / arrowhead polygon (strictly concave at index 2)
    corners_concave = np.array([
        [100.0, 100.0],
        [300.0, 100.0],
        [200.0, 180.0],  # Inward-pointing concave vertex
        [100.0, 300.0],
    ])
    is_valid, err = validator.validate(corners_concave)
    assert is_valid is False
    assert "non-convex" in err

