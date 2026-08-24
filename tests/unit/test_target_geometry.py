"""Unit tests for target geometry definitions."""

import pytest
import numpy as np

from skyvanta.core.exceptions import GeometryError
from skyvanta.target.geometry import TargetGeometry


def test_target_geometry_construction():
    geom = TargetGeometry(marker_size_m=0.20)
    pts = geom.get_object_points()

    assert pts.shape == (4, 3)
    # Check bounds are [-0.1, +0.1]
    assert np.allclose(pts[0], [-0.10, -0.10, 0.0])  # Top-Left
    assert np.allclose(pts[1], [+0.10, -0.10, 0.0])  # Top-Right
    assert np.allclose(pts[2], [+0.10, +0.10, 0.0])  # Bottom-Right
    assert np.allclose(pts[3], [-0.10, +0.10, 0.0])  # Bottom-Left


def test_invalid_target_geometry_size():
    with pytest.raises(GeometryError, match="Marker size must be strictly positive"):
        TargetGeometry(marker_size_m=-0.5)

    with pytest.raises(GeometryError, match="Marker size must be strictly positive"):
        TargetGeometry(marker_size_m=0.0)
