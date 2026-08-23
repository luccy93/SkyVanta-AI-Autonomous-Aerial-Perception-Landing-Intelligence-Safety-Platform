"""Parsing utilities for raw detection outputs."""

from typing import Any, List, Optional, Set, Tuple
from skyvanta.core.types import BoundingBox, Detection, DetectionSource


class DetectionParser:
    """Parses and sanitizes raw model coordinates and bounding boxes."""

    @staticmethod
    def parse_xyxy_box(
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        confidence: float,
        class_name: str = "drone",
        class_id: Optional[int] = None,
        source: DetectionSource = DetectionSource.YOLO,
        frame_id: Optional[int] = None,
        timestamp_sec: Optional[float] = None,
        min_size: float = 1.0,
    ) -> Optional[Detection]:
        """Validates and constructs a typed Detection from raw coordinates.

        Returns None if coordinates are malformed, inverted, or below min_size.
        """
        bbox = BoundingBox(x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2))
        if not bbox.is_valid(min_size=min_size):
            return None

        # Clamp confidence to [0.0, 1.0]
        clamped_conf = max(0.0, min(1.0, float(confidence)))

        return Detection(
            bbox=bbox,
            confidence=clamped_conf,
            class_name=str(class_name),
            class_id=class_id,
            source=source,
            frame_id=frame_id,
            timestamp_sec=timestamp_sec,
        )

    @staticmethod
    def filter_by_class(
        detections: List[Detection],
        allowed_classes: Set[str],
    ) -> List[Detection]:
        """Filters detections by class name whitelist."""
        if not allowed_classes:
            return detections
        return [d for d in detections if d.class_name in allowed_classes]

    @staticmethod
    def filter_by_confidence(
        detections: List[Detection],
        min_confidence: float,
    ) -> List[Detection]:
        """Filters detections by minimum confidence threshold."""
        return [d for d in detections if d.confidence >= min_confidence]
