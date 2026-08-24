"""OpenCV ArUco fiducial marker detector."""

from typing import List, Optional
import cv2
import numpy as np

from skyvanta.core.config import ArucoConfig
from skyvanta.core.exceptions import DetectorError
from skyvanta.core.logging import get_logger
from skyvanta.core.types import LandingTarget
from skyvanta.target.base import BaseFiducialDetector
from skyvanta.target.validation import CornerValidator

logger = get_logger("skyvanta.target.aruco")


class ArucoFiducialDetector(BaseFiducialDetector):
    """Detects and decodes OpenCV ArUco markers in camera frames."""

    def __init__(self, config: Optional[ArucoConfig] = None):
        self.config = config or ArucoConfig()
        self.validator = CornerValidator()

        dict_attr = getattr(cv2.aruco, self.config.dictionary, None)
        if dict_attr is None:
            raise DetectorError(f"Unknown or unsupported ArUco dictionary: {self.config.dictionary}")

        self.dictionary = cv2.aruco.getPredefinedDictionary(dict_attr)

        if hasattr(cv2.aruco, "DetectorParameters"):
            self.params = cv2.aruco.DetectorParameters()
        else:
            self.params = cv2.aruco.DetectorParameters_create()

        self.params.adaptiveThreshWinSizeMin = self.config.adaptive_thresh_win_size_min
        self.params.adaptiveThreshWinSizeMax = self.config.adaptive_thresh_win_size_max
        self.params.adaptiveThreshWinSizeStep = self.config.adaptive_thresh_win_size_step

        if hasattr(cv2.aruco, "ArucoDetector"):
            self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.params)
        else:
            self.detector = None

    def detect(
        self,
        frame_bgr: np.ndarray,
        timestamp_sec: float = 0.0,
        frame_id: int = 0,
    ) -> List[LandingTarget]:
        """Detects ArUco markers in the provided BGR image frame."""
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY) if len(frame_bgr.shape) == 3 else frame_bgr

        if self.detector is not None:
            corners_list, ids, _ = self.detector.detectMarkers(gray)
        else:
            corners_list, ids, _ = cv2.aruco.detectMarkers(gray, self.dictionary, parameters=self.params)

        if ids is None or len(corners_list) == 0:
            return []

        targets: List[LandingTarget] = []
        for i, raw_corners in enumerate(corners_list):
            marker_id = int(ids[i][0])
            pts = raw_corners.reshape(4, 2)

            is_valid, err_msg = self.validator.validate(pts)
            if not is_valid:
                logger.warning("Rejected degenerate ArUco marker ID %d: %s", marker_id, err_msg)
                continue

            cx = float(np.mean(pts[:, 0]))
            cy = float(np.mean(pts[:, 1]))
            corner_tuples = [(float(p[0]), float(p[1])) for p in pts]

            targets.append(
                LandingTarget(
                    target_id=marker_id,
                    marker_family=self.config.dictionary,
                    marker_id=marker_id,
                    corners=corner_tuples,
                    center=(cx, cy),
                    confidence=1.0,
                    timestamp_sec=timestamp_sec,
                    frame_id=frame_id,
                    source="aruco",
                )
            )

        return targets
