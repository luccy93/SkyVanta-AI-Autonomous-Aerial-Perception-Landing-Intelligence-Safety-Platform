"""Candidate scoring formula and evaluation metrics.

SCORING FORMULA:
The composite candidate score S_candidate represents confidence in a target candidate (0.0 to 1.0)
computed as a weighted sum of independent visual evidence cues:

    S_candidate = clamp(
        w_det * C_det +
        w_mot * C_mot +
        w_flow * C_flow +
        w_iou * IoU,
        0.0, 1.0
    )

Where:
- C_det: Semantic detector confidence score (0.0 if not detected by YOLO)
- C_mot: Motion contrast confidence score (0.0 if not detected by background subtractor)
- C_flow: Local optical flow energy in candidate ROI (0.0 to 1.0)
- IoU: Spatial intersection-over-union between semantic box and motion box (0.0 if isolated)
- w_det, w_mot, w_flow, w_iou: Configurable weighting terms summing to 1.0
"""

from typing import Optional
from skyvanta.core.config import FusionConfig


class CandidateScorer:
    """Computes transparent, weighted candidate scores for target candidates."""

    def __init__(self, config: Optional[FusionConfig] = None):
        self.config = config or FusionConfig()

    def score(
        self,
        det_conf: float = 0.0,
        mot_conf: float = 0.0,
        flow_conf: float = 0.0,
        iou: float = 0.0,
    ) -> float:
        """Calculates normalized candidate score based on configured weights.

        Args:
            det_conf: Detector confidence in [0.0, 1.0]
            mot_conf: Motion confidence in [0.0, 1.0]
            flow_conf: Optical flow evidence in [0.0, 1.0]
            iou: Spatial overlap between detector and motion in [0.0, 1.0]

        Returns:
            candidate_score in [0.0, 1.0]
        """
        w_det = self.config.weight_detection
        w_mot = self.config.weight_motion
        w_flow = self.config.weight_flow
        w_iou = self.config.weight_iou

        raw_score = (
            w_det * det_conf +
            w_mot * mot_conf +
            w_flow * flow_conf +
            w_iou * iou
        )

        # Normalize score if only a subset of sources is active
        # Boost overlapping multi-cue detections
        if det_conf > 0.0 and mot_conf > 0.0 and iou > 0.1:
            raw_score = min(1.0, raw_score + 0.15)

        return max(0.0, min(1.0, float(raw_score)))
