"""Unit tests for fiducial marker detectors and factory."""

import pytest
import numpy as np

from skyvanta.core.config import LandingTargetConfig
from skyvanta.core.exceptions import DetectorError
from skyvanta.target.aruco import ArucoFiducialDetector
from skyvanta.target.apriltag import AprilTagFiducialDetector
from skyvanta.target.factory import FiducialDetectorFactory
from skyvanta.target.mock import MockFiducialDetector


def test_mock_detector():
    mock = MockFiducialDetector()
    mock.set_synthetic_target(center=(640.0, 360.0), size_px=80.0, marker_id=42)

    fake_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    targets = mock.detect(fake_frame, timestamp_sec=1.5, frame_id=10)

    assert len(targets) == 1
    t = targets[0]
    assert t.target_id == 42
    assert t.marker_id == 42
    assert t.center == (640.0, 360.0)
    assert len(t.corners) == 4
    assert t.timestamp_sec == 1.5
    assert t.frame_id == 10

    mock.clear()
    assert len(mock.detect(fake_frame)) == 0


def test_detector_factory():
    cfg_aruco = LandingTargetConfig(detector_type="aruco")
    det_aruco = FiducialDetectorFactory.create(cfg_aruco)
    assert isinstance(det_aruco, ArucoFiducialDetector)

    cfg_apriltag = LandingTargetConfig(detector_type="apriltag")
    det_apriltag = FiducialDetectorFactory.create(cfg_apriltag)
    assert isinstance(det_apriltag, AprilTagFiducialDetector)

    cfg_mock = LandingTargetConfig(detector_type="mock")
    det_mock = FiducialDetectorFactory.create(cfg_mock)
    assert isinstance(det_mock, MockFiducialDetector)

    cfg_invalid = LandingTargetConfig(detector_type="unknown_detector")
    with pytest.raises(DetectorError, match="Unsupported fiducial detector type"):
        FiducialDetectorFactory.create(cfg_invalid)
