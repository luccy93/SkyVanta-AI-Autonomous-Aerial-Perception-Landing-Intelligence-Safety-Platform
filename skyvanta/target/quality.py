"""Pose estimation quality assessment and confidence scoring."""

import math
from typing import Optional
from skyvanta.core.config import PoseQualityConfig


class PoseQualityEvaluator:
    """Computes a transparent, bounded [0.0, 1.0] quality score for a solved 6-DoF pose."""

    def __init__(self, config: Optional[PoseQualityConfig] = None):
        self.config = config or PoseQualityConfig()

    def evaluate(
        self,
        reprojection_error_rms: float,
        corner_area_px: float,
        depth_m: float,
        detector_confidence: float = 1.0,
    ) -> float:
        """Evaluates pose quality based on reprojection accuracy, pixel resolution, and depth.

        Returns:
            Quality rating in range [0.0, 1.0].
        """
        # 1. Reprojection accuracy term (linear decay to zero at max threshold)
        reproj_term = max(
            0.0,
            1.0 - (reprojection_error_rms / self.config.max_reproj_error_for_zero_quality)
        )

        # 2. Pixel resolution / area coverage term
        area_ratio = corner_area_px / max(1.0, self.config.min_corner_area_px * 8.0)
        area_term = max(0.2, min(1.0, math.sqrt(area_ratio)))

        # 3. Depth validity term
        depth_term = 1.0 if depth_m > 0.05 else 0.0

        # Weighted combination
        quality = (
            0.50 * reproj_term +
            0.25 * area_term +
            0.25 * float(detector_confidence)
        ) * depth_term

        return float(max(0.0, min(1.0, quality)))
