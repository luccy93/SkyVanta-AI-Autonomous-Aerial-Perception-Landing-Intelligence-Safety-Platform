"""Spatial gating algorithms for rejecting impossible detection-track pairings."""

import math
from typing import Optional
from skyvanta.core.config import AssociationConfig
from skyvanta.core.types import BoundingBox


class SpatialGater:
    """Validates physical/image-space proximity constraints before data association."""

    def __init__(self, config: Optional[AssociationConfig] = None):
        self.config = config or AssociationConfig()

    def is_valid_pair(self, track_box: BoundingBox, det_box: BoundingBox) -> bool:
        """Evaluates whether a candidate detection is within the spatial gate of a track."""
        if not track_box.is_valid() or not det_box.is_valid():
            return False

        # Center Euclidean distance constraint
        tcx, tcy = track_box.center
        dcx, dcy = det_box.center
        dist = math.hypot(dcx - tcx, dcy - tcy)
        if dist > self.config.max_center_distance_px:
            return False

        # Scale / area ratio constraint
        t_area = max(1.0, track_box.area)
        d_area = max(1.0, det_box.area)
        scale_ratio = d_area / t_area
        if scale_ratio < self.config.min_scale_ratio or scale_ratio > self.config.max_scale_ratio:
            return False

        return True
