"""Abstract base interfaces for fiducial and landing target detection."""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from skyvanta.core.types import LandingTarget


class BaseFiducialDetector(ABC):
    """Abstract interface for fiducial marker detectors (ArUco, AprilTag, Mock)."""

    @abstractmethod
    def detect(
        self,
        frame_bgr: np.ndarray,
        timestamp_sec: float = 0.0,
        frame_id: int = 0,
    ) -> List[LandingTarget]:
        """Detects visual fiducial markers in an image frame.

        Args:
            frame_bgr: Input BGR image array.
            timestamp_sec: Frame capture timestamp in seconds.
            frame_id: Sequential video frame index.

        Returns:
            List of detected and decoded LandingTarget objects with 4 image corners.
        """
        pass
