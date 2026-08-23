"""Deterministic mock detector for unit testing and offline simulation."""

from typing import Any, Callable, Dict, List, Optional
import numpy as np
from skyvanta.core.types import BoundingBox, Detection, DetectionSource
from skyvanta.perception.detection.base import BaseDetector


class MockDetector(BaseDetector):
    """Mock detector returning predefined or programmatic detections."""

    def __init__(
        self,
        canned_detections: Optional[List[Detection]] = None,
        generator_fn: Optional[Callable[[np.ndarray, Optional[int]], List[Detection]]] = None,
        available: bool = True,
    ):
        self._canned_detections = canned_detections or []
        self._generator_fn = generator_fn
        self._available = available
        self.call_count = 0

    @property
    def is_available(self) -> bool:
        return self._available

    def set_available(self, available: bool) -> None:
        self._available = available

    def set_canned_detections(self, detections: List[Detection]) -> None:
        self._canned_detections = detections

    def detect(
        self,
        frame_bgr: np.ndarray,
        confidence_threshold: Optional[float] = None,
        frame_id: Optional[int] = None,
        timestamp_sec: Optional[float] = None,
    ) -> List[Detection]:
        self.call_count += 1
        if not self._available:
            return []

        if self._generator_fn is not None:
            dets = self._generator_fn(frame_bgr, frame_id)
        else:
            dets = list(self._canned_detections)

        conf_thresh = confidence_threshold or 0.0
        return [d for d in dets if d.confidence >= conf_thresh]

    def get_info(self) -> Dict[str, Any]:
        return {
            "backend": "mock",
            "is_available": self._available,
            "call_count": self.call_count,
        }
