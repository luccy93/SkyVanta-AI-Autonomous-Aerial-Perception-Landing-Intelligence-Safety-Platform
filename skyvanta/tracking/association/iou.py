"""IoU-based bipartite data association strategy."""

from typing import List, Optional, Tuple
import numpy as np

from skyvanta.core.config import AssociationConfig
from skyvanta.core.types import BoundingBox, Track
from skyvanta.tracking.association.base import BaseAssociator
from skyvanta.tracking.association.gating import SpatialGater


class IoUAssociator(BaseAssociator):
    """Associates detections to tracks using spatial IoU matrix and greedy bipartite matching."""

    def __init__(self, config: Optional[AssociationConfig] = None):
        self.config = config or AssociationConfig()
        self.gater = SpatialGater(self.config)

    def associate(
        self,
        tracks: List[Track],
        detections: List[BoundingBox],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Matches tracks to incoming detections.

        Returns:
            (matches, unmatched_tracks, unmatched_detections)
        """
        if not tracks:
            return [], [], list(range(len(detections)))
        if not detections:
            return [], list(range(len(tracks))), []

        num_tracks = len(tracks)
        num_dets = len(detections)

        # Build IoU similarity matrix
        iou_matrix = np.zeros((num_tracks, num_dets), dtype=np.float32)

        for t_idx, track in enumerate(tracks):
            track_box = track.predicted_bbox if track.predicted_bbox is not None else track.bbox
            for d_idx, det_box in enumerate(detections):
                if self.gater.is_valid_pair(track_box, det_box):
                    iou_matrix[t_idx, d_idx] = track_box.iou(det_box)
                else:
                    iou_matrix[t_idx, d_idx] = 0.0

        # Greedy bipartite matching on highest IoU
        matches: List[Tuple[int, int]] = []
        matched_tracks = set()
        matched_dets = set()

        # Flatten and sort candidate pairs descending by IoU
        pairs = []
        for t_idx in range(num_tracks):
            for d_idx in range(num_dets):
                score = float(iou_matrix[t_idx, d_idx])
                if score >= self.config.min_iou:
                    pairs.append((score, t_idx, d_idx))

        pairs.sort(key=lambda x: x[0], reverse=True)

        for score, t_idx, d_idx in pairs:
            if t_idx not in matched_tracks and d_idx not in matched_dets:
                matches.append((t_idx, d_idx))
                matched_tracks.add(t_idx)
                matched_dets.add(d_idx)

        unmatched_tracks = [t for t in range(num_tracks) if t not in matched_tracks]
        unmatched_dets = [d for d in range(num_dets) if d not in matched_dets]

        return matches, unmatched_tracks, unmatched_dets
