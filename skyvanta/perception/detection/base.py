"""Abstract base class for object and target detectors."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import numpy as np
from skyvanta.core.types import Detection


class BaseDetector(ABC):
    """Abstract interface for visual object detectors."""

    @abstractmethod
    def detect(
        self,
        frame_bgr: np.ndarray,
        confidence_threshold: Optional[float] = None,
        frame_id: Optional[int] = None,
        timestamp_sec: Optional[float] = None,
    ) -> List[Detection]:
        """Runs object detection on a BGR image frame.

        Args:
            frame_bgr: Input BGR image array (H, W, 3)
            confidence_threshold: Optional override for detection score threshold
            frame_id: Optional sequential frame identifier
            timestamp_sec: Optional video timestamp

        Returns:
            List of detected `Detection` objects.
        """
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if detector backend and model weights are ready for inference."""
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Returns diagnostic metadata about the loaded detector backend."""
        pass
