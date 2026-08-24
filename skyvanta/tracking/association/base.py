"""Abstract base class for data association algorithms."""

from abc import ABC, abstractmethod
from typing import List, Tuple
from skyvanta.core.types import BoundingBox, Candidate, Detection, Track


class BaseAssociator(ABC):
    """Abstract interface for associating detections with existing tracks."""

    @abstractmethod
    def associate(
        self,
        tracks: List[Track],
        detections: List[BoundingBox],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Matches tracks to incoming detections.

        Args:
            tracks: List of active Track objects (using predicted_bbox)
            detections: List of candidate bounding boxes from perception

        Returns:
            (matches, unmatched_tracks, unmatched_detections)
            where matches is a list of (track_index, detection_index) pairs.
        """
        pass
