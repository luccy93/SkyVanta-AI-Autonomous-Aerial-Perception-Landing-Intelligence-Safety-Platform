"""Factory for instantiating fiducial target detectors."""

from typing import Optional
from skyvanta.core.config import LandingTargetConfig
from skyvanta.core.exceptions import DetectorError
from skyvanta.target.apriltag import AprilTagFiducialDetector
from skyvanta.target.aruco import ArucoFiducialDetector
from skyvanta.target.base import BaseFiducialDetector
from skyvanta.target.mock import MockFiducialDetector


class FiducialDetectorFactory:
    """Instantiates the appropriate fiducial detector backend based on configuration."""

    @staticmethod
    def create(config: Optional[LandingTargetConfig] = None) -> BaseFiducialDetector:
        cfg = config or LandingTargetConfig()
        dtype = cfg.detector_type.lower()

        if dtype == "aruco":
            return ArucoFiducialDetector(cfg.aruco)
        elif dtype == "apriltag":
            return AprilTagFiducialDetector(cfg.april_tag)
        elif dtype == "mock":
            return MockFiducialDetector()
        else:
            raise DetectorError(f"Unsupported fiducial detector type: '{cfg.detector_type}' (valid: aruco, apriltag, mock)")
