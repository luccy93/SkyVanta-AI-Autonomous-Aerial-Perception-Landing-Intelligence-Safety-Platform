"""AprilTag fiducial marker detector adapter."""

from typing import List, Optional
import cv2
import numpy as np

from skyvanta.core.config import AprilTagConfig
from skyvanta.core.logging import get_logger
from skyvanta.core.types import LandingTarget
from skyvanta.target.base import BaseFiducialDetector
from skyvanta.target.validation import CornerValidator

logger = get_logger("skyvanta.target.apriltag")


class AprilTagFiducialDetector(BaseFiducialDetector):
    """AprilTag detector supporting pupil_apriltags or OpenCV AprilTag dictionary."""

    def __init__(self, config: Optional[AprilTagConfig] = None):
        self.config = config or AprilTagConfig()
        self.validator = CornerValidator()

        self._pupil_detector = None
        self._cv2_aruco_apriltag = None

        # Check pupil_apriltags / apriltag
        try:
            from pupil_apriltags import Detector
            self._pupil_detector = Detector(
                families=self.config.family,
                nthreads=self.config.threads,
                quad_decimate=self.config.quad_decimate,
            )
            logger.info("Initialized pupil_apriltags detector for family '%s'", self.config.family)
        except ImportError:
            # Fallback to OpenCV AprilTag dictionary if available
            family_map = {
                "tag36h11": getattr(cv2.aruco, "DICT_APRILTAG_36h11", None),
                "tag25h9": getattr(cv2.aruco, "DICT_APRILTAG_25h9", None),
                "tag16h5": getattr(cv2.aruco, "DICT_APRILTAG_16h5", None),
            }
            dict_attr = family_map.get(self.config.family.lower())
            if dict_attr is not None:
                dictionary = cv2.aruco.getPredefinedDictionary(dict_attr)
                params = cv2.aruco.DetectorParameters() if hasattr(cv2.aruco, "DetectorParameters") else cv2.aruco.DetectorParameters_create()
                if hasattr(cv2.aruco, "ArucoDetector"):
                    self._cv2_aruco_apriltag = cv2.aruco.ArucoDetector(dictionary, params)
                else:
                    self._cv2_aruco_apriltag = (dictionary, params)
                logger.info("Initialized OpenCV cv2.aruco AprilTag fallback for family '%s'", self.config.family)
            else:
                logger.warning("No native AprilTag library or OpenCV dictionary found for '%s'", self.config.family)

    @property
    def is_available(self) -> bool:
        """Returns True if an AprilTag backend is ready."""
        return self._pupil_detector is not None or self._cv2_aruco_apriltag is not None

    def detect(
        self,
        frame_bgr: np.ndarray,
        timestamp_sec: float = 0.0,
        frame_id: int = 0,
    ) -> List[LandingTarget]:
        """Detects AprilTag markers in the given image frame."""
        if frame_bgr is None or frame_bgr.size == 0 or not self.is_available:
            return []

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY) if len(frame_bgr.shape) == 3 else frame_bgr
        targets: List[LandingTarget] = []

        if self._pupil_detector is not None:
            results = self._pupil_detector.detect(gray)
            for res in results:
                pts = res.corners.reshape(4, 2)
                is_valid, err = self.validator.validate(pts)
                if not is_valid:
                    continue
                cx, cy = float(res.center[0]), float(res.center[1])
                corner_tuples = [(float(p[0]), float(p[1])) for p in pts]
                targets.append(
                    LandingTarget(
                        target_id=int(res.tag_id),
                        marker_family=self.config.family,
                        marker_id=int(res.tag_id),
                        corners=corner_tuples,
                        center=(cx, cy),
                        confidence=float(getattr(res, "decision_margin", 1.0) / 100.0) if hasattr(res, "decision_margin") else 1.0,
                        timestamp_sec=timestamp_sec,
                        frame_id=frame_id,
                        source="apriltag",
                    )
                )
        elif self._cv2_aruco_apriltag is not None:
            if hasattr(self._cv2_aruco_apriltag, "detectMarkers"):
                corners_list, ids, _ = self._cv2_aruco_apriltag.detectMarkers(gray)
            else:
                d, p = self._cv2_aruco_apriltag
                corners_list, ids, _ = cv2.aruco.detectMarkers(gray, d, parameters=p)

            if ids is not None and len(corners_list) > 0:
                for i, raw_corners in enumerate(corners_list):
                    marker_id = int(ids[i][0])
                    pts = raw_corners.reshape(4, 2)
                    is_valid, _ = self.validator.validate(pts)
                    if not is_valid:
                        continue
                    cx = float(np.mean(pts[:, 0]))
                    cy = float(np.mean(pts[:, 1]))
                    corner_tuples = [(float(p[0]), float(p[1])) for p in pts]
                    targets.append(
                        LandingTarget(
                            target_id=marker_id,
                            marker_family=self.config.family,
                            marker_id=marker_id,
                            corners=corner_tuples,
                            center=(cx, cy),
                            confidence=1.0,
                            timestamp_sec=timestamp_sec,
                            frame_id=frame_id,
                            source="apriltag",
                        )
                    )

        return targets
