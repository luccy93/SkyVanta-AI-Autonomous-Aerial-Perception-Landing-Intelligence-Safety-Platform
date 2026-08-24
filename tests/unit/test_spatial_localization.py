"""Unit tests for SpatialLocalizationService and multi-frame target localization."""

import math
import pytest
import numpy as np

from skyvanta.core.config import CameraExtrinsicsConfig, SpatialConfig
from skyvanta.core.types import FrameId, Pose6D, PoseEstimateResult
from skyvanta.spatial.localization import SpatialLocalizationService
from skyvanta.spatial.se3 import SE3Transform


@pytest.fixture
def localization_service():
    cfg = SpatialConfig(
        camera_extrinsics=CameraExtrinsicsConfig(
            enabled=True,
            parent_frame="BODY",
            child_frame="CAMERA",
            translation_m=[0.10, 0.0, -0.05],
            rotation_rpy_deg=[0.0, 0.0, 0.0],
        )
    )
    return SpatialLocalizationService(config=cfg)


def test_localize_target_to_body_nominal(localization_service):
    # Dummy valid camera-relative pose
    pose_cam = Pose6D(
        x=0.0, y=0.0, z=2.0,
        rotation_matrix=np.eye(3).tolist(),
        rvec=(0.0, 0.0, 0.0),
        quaternion=(1.0, 0.0, 0.0, 0.0),
        euler_deg=(0.0, 0.0, 0.0),
        euler_rad=(0.0, 0.0, 0.0),
        range_m=2.0,
        reprojection_error_rms=0.15,
        reprojection_error_max=0.15,
        pose_quality=0.98,
        is_valid=True,
        timestamp_sec=2.5,
        frame_id=20,
        target_id=5,
        solver_method="IPPE",
    )
    pose_res = PoseEstimateResult(
        timestamp_sec=2.5,
        frame_id=20,
        target_id=5,
        pose=pose_cam,
        reprojection_error_rms=0.15,
        pose_quality=0.98,
        is_valid=True,
    )

    result = localization_service.localize_target(pose_res, target_frame=FrameId.BODY)

    assert result.is_valid is True
    assert result.source_frame == FrameId.CAMERA
    assert result.target_frame == FrameId.BODY
    assert result.pose is not None
    # Position in BODY: [0, 0, 2.0] + [0.10, 0.0, -0.05] = [0.10, 0.0, 1.95]
    assert pytest.approx(result.pose.x, abs=1e-3) == 0.10
    assert pytest.approx(result.pose.y, abs=1e-3) == 0.0
    assert pytest.approx(result.pose.z, abs=1e-3) == 1.95
    assert result.is_world_relative is False


def test_localize_target_world_unavailable(localization_service):
    pose_cam = Pose6D(
        x=0.0, y=0.0, z=2.0,
        rotation_matrix=np.eye(3).tolist(),
        rvec=(0.0, 0.0, 0.0),
        quaternion=(1.0, 0.0, 0.0, 0.0),
        euler_deg=(0.0, 0.0, 0.0),
        euler_rad=(0.0, 0.0, 0.0),
        range_m=2.0,
        is_valid=True,
        timestamp_sec=1.0,
        frame_id=1,
        target_id=1,
        solver_method="IPPE",
    )
    pose_res = PoseEstimateResult(timestamp_sec=1.0, frame_id=1, target_id=1, pose=pose_cam, is_valid=True)

    # Request localization to WORLD when no WORLD reference is registered
    result = localization_service.localize_target(pose_res, target_frame=FrameId.WORLD)

    assert result.is_valid is False
    assert result.is_world_relative is False
    assert result.pose is None
    assert "WORLD frame reference is unavailable" in result.failure_reason


def test_localize_target_with_registered_world_reference(localization_service):
    # Register synthetic WORLD -> BODY transform (e.g. drone at North 10m, East 5m, Down -20m)
    t_world_body = SE3Transform.from_euler(
        source_frame=FrameId.BODY,
        target_frame=FrameId.WORLD,
        translation=(10.0, 5.0, -20.0),
        euler_deg=(0.0, 0.0, 0.0),
        timestamp_sec=1.0,
        is_static=False,
    )
    localization_service.register_world_reference(t_world_body)

    pose_cam = Pose6D(
        x=0.0, y=0.0, z=2.0,
        rotation_matrix=np.eye(3).tolist(),
        rvec=(0.0, 0.0, 0.0),
        quaternion=(1.0, 0.0, 0.0, 0.0),
        euler_deg=(0.0, 0.0, 0.0),
        euler_rad=(0.0, 0.0, 0.0),
        range_m=2.0,
        is_valid=True,
        timestamp_sec=1.0,
        frame_id=1,
        target_id=1,
        solver_method="IPPE",
    )
    pose_res = PoseEstimateResult(timestamp_sec=1.0, frame_id=1, target_id=1, pose=pose_cam, is_valid=True)

    result = localization_service.localize_target(pose_res, target_frame=FrameId.WORLD)

    assert result.is_valid is True
    assert result.is_world_relative is True
    assert result.pose is not None
    # WORLD pos = [10, 5, -20] + [0.10, 0.0, 1.95] = [10.10, 5.0, -18.05]
    assert pytest.approx(result.pose.x, abs=1e-3) == 10.10
    assert pytest.approx(result.pose.y, abs=1e-3) == 5.00
    assert pytest.approx(result.pose.z, abs=1e-3) == -18.05
