"""Pytest fixtures for SkyVanta test suite."""

import pytest
import numpy as np
from skyvanta.core.config import SkyVantaConfig
from skyvanta.core.types import BoundingBox


@pytest.fixture
def default_config() -> SkyVantaConfig:
    """Returns a default SkyVanta configuration instance."""
    return SkyVantaConfig()


@pytest.fixture
def sample_frame_bgr() -> np.ndarray:
    """Generates a dummy 720x1280 BGR test image."""
    return np.zeros((720, 1280, 3), dtype=np.uint8)


@pytest.fixture
def sample_bbox() -> BoundingBox:
    """Returns a sample 2D bounding box."""
    return BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
