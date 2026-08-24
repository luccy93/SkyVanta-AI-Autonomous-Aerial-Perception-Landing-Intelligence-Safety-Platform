"""Deterministic Mock Fiducial Detector for offline unit and integration testing."""

from typing import List, Optional, Tuple
import numpy as np

from skyvanta.core.types import LandingTarget
from skyvanta.target.base import BaseFiducialDetector


class MockFiducialDetector(BaseFiducialDetector):
    """Deterministic mock detector returning configured or synthetic landing targets."""

    def __init__(self, predefined_targets: Optional[List[LandingTarget]] = None):
        self._targets: List[LandingTarget] = predefined_targets or []

    def set_targets(self, targets: List[LandingTarget]) -> None:
        """Sets the targets returned on subsequent detect calls."""
        self._targets = targets

    def set_synthetic_target(
        self,
        center: Tuple[float, float],
        size_px: float,
        marker_id: int = 1,
        marker_family: str = "mock_tag",
        confidence: float = 1.0,
    ) -> None:
        """Creates and sets a square 4-corner mock target centered at (cx, cy)."""
        cx, cy = center
        s = size_px / 2.0
        corners = [
            (cx - s, cy - s),  # Top-Left
            (cx + s, cy - s),  # Top-Right
            (cx + s, cy + s),  # Bottom-Right
            (cx - s, cy + s),  # Bottom-Left
        ]
        self._targets = [
            LandingTarget(
                target_id=marker_id,
                marker_family=marker_family,
                marker_id=marker_id,
                corners=corners,
                center=center,
                confidence=confidence,
                source="mock",
            )
        ]

    def clear(self) -> None:
        """Clears all configured mock targets."""
        self._targets = []

    def detect(
        self,
        frame_bgr: np.ndarray,
        timestamp_sec: float = 0.0,
        frame_id: int = 0,
    ) -> List[LandingTarget]:
        """Returns the configured mock targets with updated timestamps."""
        results = []
        for t in self._targets:
            res = t.model_copy(deep=True)
            res.timestamp_sec = timestamp_sec
            res.frame_id = frame_id
            results.append(res)
        return results
