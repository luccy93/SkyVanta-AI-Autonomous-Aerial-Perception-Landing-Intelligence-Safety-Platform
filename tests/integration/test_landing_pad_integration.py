"""Deterministic integration tests for Staged Landing-Pad Perception & 6-DoF Pose Estimation (Volume 4)."""

import math
import pytest
import numpy as np

from skyvanta.core.config import CameraConfig, LandingTargetConfig
from skyvanta.core.types import LandingTarget
from skyvanta.spatial.camera import CameraModel
from skyvanta.spatial.synthetic import SyntheticPoseGenerator
from skyvanta.target.estimator import SpatialLandingPadEstimator
from skyvanta.target.geometry import TargetGeometry
from skyvanta.target.mock import MockFiducialDetector


def test_landing_pad_estimator_end_to_end_nominal():
    """Verifies complete spatial estimation pipeline from synthetic detection to validated 6-DoF pose."""
    cam_cfg = CameraConfig(image_width=1280, image_height=720, fx=1000.0, fy=1000.0, cx=640.0, cy=360.0)
    camera = CameraModel(cam_cfg)
    geom = TargetGeometry(marker_size_m=0.20)
    obj_pts = geom.get_object_points()

    true_translation = (0.20, -0.10, 2.00)
    true_rotation = (0.0, math.radians(10.0), math.radians(-15.0))

    # Generate synthetic 2D corners for the given 6-DoF pose
    corners_2d, _ = SyntheticPoseGenerator.generate(
        camera,
        obj_pts,
        true_translation,
        true_rotation,
        noise_std_px=0.0,
    )

    # Set up mock detector with the projected corners
    corner_tuples = [(float(c[0]), float(c[1])) for c in corners_2d]
    mock_target = LandingTarget(
        target_id=7,
        marker_family="DICT_6X6_250",
        marker_id=7,
        corners=corner_tuples,
        center=(float(np.mean(corners_2d[:, 0])), float(np.mean(corners_2d[:, 1]))),
        confidence=0.98,
        source="mock",
    )
    mock_det = MockFiducialDetector([mock_target])

    config = LandingTargetConfig(detector_type="mock", camera=cam_cfg)
    estimator = SpatialLandingPadEstimator(config=config, camera_model=camera, detector=mock_det)

    fake_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    targets, pose_res, landing_pad = estimator.process(fake_frame, timestamp_sec=0.5, frame_id=15)

    assert len(targets) == 1
    assert pose_res is not None
    assert pose_res.is_valid is True
    assert pose_res.pose is not None

    # Check metric translation recovery (sub-millimeter precision on zero-noise test)
    assert pytest.approx(pose_res.pose.x, abs=1e-3) == 0.20
    assert pytest.approx(pose_res.pose.y, abs=1e-3) == -0.10
    assert pytest.approx(pose_res.pose.z, abs=1e-3) == 2.00

    # Check orientation recovery
    assert pytest.approx(pose_res.pose.euler_deg[1], abs=0.5) == 10.0
    assert pytest.approx(pose_res.pose.euler_deg[2], abs=0.5) == -15.0

    # Check unified LandingPad representation
    assert landing_pad is not None
    assert landing_pad.pad_id == 7
    assert landing_pad.marker_id == 7
    assert landing_pad.marker_size_m == 0.20
    assert landing_pad.is_trackable is True


def test_landing_pad_estimator_degenerate_corner_rejection():
    """Verifies that malformed or degenerate corners are safely caught before PnP."""
    cam_cfg = CameraConfig(image_width=1280, image_height=720, fx=1000.0, fy=1000.0, cx=640.0, cy=360.0)
    camera = CameraModel(cam_cfg)

    # Degenerate collinear corners
    corrupt_corners = [(100.0, 100.0), (150.0, 100.0), (200.0, 100.0), (250.0, 100.0)]
    mock_target = LandingTarget(
        target_id=99,
        marker_family="mock",
        marker_id=99,
        corners=corrupt_corners,
        center=(175.0, 100.0),
        confidence=0.5,
        source="mock",
    )
    mock_det = MockFiducialDetector([mock_target])

    config = LandingTargetConfig(detector_type="mock", camera=cam_cfg)
    estimator = SpatialLandingPadEstimator(config=config, camera_model=camera, detector=mock_det)

    fake_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    targets, pose_res, landing_pad = estimator.process(fake_frame)

    assert len(targets) == 1
    assert pose_res is not None
    assert pose_res.is_valid is False
    assert "Degenerate corner geometry" in pose_res.failure_reason
    assert landing_pad is None
