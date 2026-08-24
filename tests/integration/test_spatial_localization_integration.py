"""Deterministic integration tests for Spatial Coordinate Transformation and Localization (Volume 5)."""

import math
import pytest
import numpy as np

from skyvanta.core.config import CameraConfig, CameraExtrinsicsConfig, LandingTargetConfig, SpatialConfig
from skyvanta.core.types import FrameId, LandingTarget, Pose6D, PoseEstimateResult

from skyvanta.spatial.camera import CameraModel
from skyvanta.spatial.localization import SpatialLocalizationService
from skyvanta.spatial.se3 import SE3Transform
from skyvanta.spatial.synthetic import SyntheticPoseGenerator
from skyvanta.target.estimator import SpatialLandingPadEstimator
from skyvanta.target.geometry import TargetGeometry
from skyvanta.target.mock import MockFiducialDetector


def test_end_to_end_camera_to_body_spatial_localization():
    """Verifies complete pipeline from synthetic 2D perception to body-relative 6-DoF localization."""
    cam_cfg = CameraConfig(image_width=1280, image_height=720, fx=1000.0, fy=1000.0, cx=640.0, cy=360.0)
    camera = CameraModel(cam_cfg)
    geom = TargetGeometry(marker_size_m=0.20)
    obj_pts = geom.get_object_points()

    # Ground truth relative pose of landing pad in CAMERA optical frame:
    # 0.15m right (+X), 0.10m down (+Y), 2.50m forward (+Z)
    true_trans_cam = (0.15, 0.10, 2.50)
    true_rot_cam = (0.0, 0.0, 0.0)

    corners_2d, _ = SyntheticPoseGenerator.generate(
        camera,
        obj_pts,
        true_trans_cam,
        true_rot_cam,
        noise_std_px=0.0,
    )

    corner_tuples = [(float(c[0]), float(c[1])) for c in corners_2d]
    mock_target = LandingTarget(
        target_id=42,
        marker_family="DICT_6X6_250",
        marker_id=42,
        corners=corner_tuples,
        center=(float(np.mean(corners_2d[:, 0])), float(np.mean(corners_2d[:, 1]))),
        confidence=1.0,
        source="mock",
    )
    mock_det = MockFiducialDetector([mock_target])

    # 1. Run V4 PnP Estimator
    target_cfg = LandingTargetConfig(detector_type="mock", camera=cam_cfg)
    estimator = SpatialLandingPadEstimator(config=target_cfg, camera_model=camera, detector=mock_det)

    fake_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    targets, pose_result, landing_pad = estimator.process(fake_frame, timestamp_sec=3.0, frame_id=90)

    assert pose_result is not None
    assert pose_result.is_valid is True
    assert pose_result.pose is not None
    assert pytest.approx(pose_result.pose.x, abs=1e-3) == 0.15
    assert pytest.approx(pose_result.pose.y, abs=1e-3) == 0.10
    assert pytest.approx(pose_result.pose.z, abs=1e-3) == 2.50

    # 2. Run V5 Spatial Localization Service
    # Body-to-Camera Extrinsics: Camera mounted 0.20m ahead (+X), 0.05m left (-Y), 0.10m below (+Z)
    spatial_cfg = SpatialConfig(
        camera_extrinsics=CameraExtrinsicsConfig(
            enabled=True,
            parent_frame="BODY",
            child_frame="CAMERA",
            translation_m=[0.20, -0.05, 0.10],
            rotation_rpy_deg=[0.0, 0.0, 0.0],
        )
    )
    loc_service = SpatialLocalizationService(config=spatial_cfg)

    loc_result = loc_service.localize_target(pose_result, target_frame=FrameId.BODY)

    assert loc_result.is_valid is True
    assert loc_result.source_frame == FrameId.CAMERA
    assert loc_result.target_frame == FrameId.BODY
    assert loc_result.pose is not None
    assert loc_result.is_world_relative is False

    # Check transformed coordinates in BODY frame:
    # x_body = 0.15 + 0.20 = 0.35m
    # y_body = 0.10 - 0.05 = 0.05m
    # z_body = 2.50 + 0.10 = 2.60m
    assert pytest.approx(loc_result.pose.x, abs=1e-3) == 0.35
    assert pytest.approx(loc_result.pose.y, abs=1e-3) == 0.05
    assert pytest.approx(loc_result.pose.z, abs=1e-3) == 2.60


def test_world_frame_unregistered_rejection():
    """Verifies that requesting world-relative localization safely and explicitly rejects when no world reference exists."""
    spatial_cfg = SpatialConfig()
    loc_service = SpatialLocalizationService(config=spatial_cfg)

    # Valid pose estimate
    pose_cam = Pose6D(
        x=0.0, y=0.0, z=3.0,
        rotation_matrix=np.eye(3).tolist(),
        rvec=(0.0, 0.0, 0.0),
        quaternion=(1.0, 0.0, 0.0, 0.0),
        euler_deg=(0.0, 0.0, 0.0),
        euler_rad=(0.0, 0.0, 0.0),
        range_m=3.0,
        is_valid=True,
        timestamp_sec=1.0,
        frame_id=1,
        target_id=1,
        solver_method="IPPE",
    )
    pose_res = PoseEstimateResult(timestamp_sec=1.0, frame_id=1, target_id=1, pose=pose_cam, is_valid=True)

    loc_result = loc_service.localize_target(pose_res, target_frame=FrameId.WORLD)

    assert loc_result.is_valid is False
    assert loc_result.is_world_relative is False
    assert loc_result.pose is None
    assert "WORLD frame reference is unavailable" in loc_result.failure_reason
