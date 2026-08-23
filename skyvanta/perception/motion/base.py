"""Abstract base class for motion detection algorithms."""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
from skyvanta.core.types import MotionCandidate


class BaseMotionDetector(ABC):
    """Abstract interface for foreground motion candidate detection."""

    @abstractmethod
    def detect(self, frame_bgr: np.ndarray) -> List[MotionCandidate]:
        """Processes a video frame and extracts candidate motion bounding boxes."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Resets temporal background model and internal history."""
        pass
