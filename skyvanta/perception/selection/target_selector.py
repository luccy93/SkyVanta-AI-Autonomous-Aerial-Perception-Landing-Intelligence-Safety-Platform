"""Target selection heuristics from fused candidate lists."""

from typing import List, Optional, Tuple
from skyvanta.core.config import TargetSelectionConfig
from skyvanta.core.types import Candidate


class TargetSelector:
    """Selects the primary target candidate based on confidence score and spatial bounds."""

    def __init__(self, config: Optional[TargetSelectionConfig] = None):
        self.config = config or TargetSelectionConfig()

    def select(
        self,
        candidates: List[Candidate],
        frame_shape: Optional[Tuple[int, int]] = None,
    ) -> Optional[Candidate]:
        """Filters and selects the highest scoring valid target candidate.

        Returns:
            The selected `Candidate` or None if no candidate passes criteria.
        """
        if not candidates:
            return None

        for cand in candidates:
            # Check minimum candidate score
            if cand.candidate_score < self.config.min_candidate_score:
                continue

            # Check bounding box validity
            if not cand.bbox.is_valid():
                continue

            # Check frame-relative geometric constraints if frame_shape provided
            if frame_shape is not None:
                h, w = frame_shape[:2]
                frame_area = float(w * h)
                box_area_ratio = cand.bbox.area / max(1.0, frame_area)

                if box_area_ratio < self.config.min_box_area_ratio:
                    continue
                if box_area_ratio > self.config.max_box_area_ratio:
                    continue

                # Check vertical cutoff if configured
                if cand.bbox.center[1] > h * self.config.roi_top_cutoff_ratio:
                    continue

            # Candidate passes all criteria
            return cand

        return None
