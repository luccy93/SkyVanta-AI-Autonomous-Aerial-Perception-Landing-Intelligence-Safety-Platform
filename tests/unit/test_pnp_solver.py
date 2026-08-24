"""Unit tests for Perspective-n-Point (PnP) 6-DoF pose solver."""

import math
import pytest
import numpy as np

from skyvanta.core.config import CameraConfig, PnPConfig
from skyvanta.spatial.camera import CameraModel
from skyvanta.spatial.pnp import PnPPoseSolver
from skyvanta.spatial.synthetic import SyntheticPoseGenerator
from skyvanta.target.geometry import TargetGeometry


@pytest.fixture
def test_camera():
    cfg = CameraConfig(
        image_width=1280,
        image_height=720,
        fx=1000.0,
        fy=1000.0,
        cx=640.0,
        cy=360.0,
        distortion_coefficients=[0.0, 0.0, 0.0, 0.0, 0.0],
    )
    return CameraModel(cfg)


def test_pnp_solve_pure_translation(test_camera):
    geom = TargetGeometry(marker_size_m=0.20)
    obj_pts = geom.get_object_points()
    solver = PnPPoseSolver(PnPConfig(solver="IPPE"))

    true_translation = (0.25, -0.15, 2.50)  # 2.5 meters away
    true_rotation = (0.0, 0.0, 0.0)

    proj_corners, true_pose = SyntheticPoseGenerator.generate(
        test_camera,
        obj_pts,
        true_translation,
        true_rotation,
        noise_std_px=0.0,
    )

    res = solver.solve(obj_pts, proj_corners, test_camera, target_id=1)

    assert res.is_valid is True
    assert res.pose is not None
    assert pytest.approx(res.pose.x, abs=1e-3) == 0.25
    assert pytest.approx(res.pose.y, abs=1e-3) == -0.15
    assert pytest.approx(res.pose.z, abs=1e-3) == 2.50
    assert res.pose.reprojection_error_rms < 0.01
    assert res.pose_quality > 0.95


def test_pnp_solve_rotated_target(test_camera):
    geom = TargetGeometry(marker_size_m=0.20)
    obj_pts = geom.get_object_points()
    solver = PnPPoseSolver(PnPConfig(solver="IPPE"))

    true_translation = (0.0, 0.0, 1.50)
    true_euler_rad = (math.radians(15.0), math.radians(-10.0), math.radians(25.0))

    proj_corners, _ = SyntheticPoseGenerator.generate(
        test_camera,
        obj_pts,
        true_translation,
        true_euler_rad,
        noise_std_px=0.0,
    )

    res = solver.solve(obj_pts, proj_corners, test_camera, target_id=1)

    assert res.is_valid is True
    assert res.pose is not None
    assert pytest.approx(res.pose.z, abs=0.01) == 1.50
    roll_deg, pitch_deg, yaw_deg = res.pose.euler_deg
    assert pytest.approx(roll_deg, abs=0.5) == 15.0
    assert pytest.approx(pitch_deg, abs=0.5) == -10.0
    assert pytest.approx(yaw_deg, abs=0.5) == 25.0


def test_pnp_solve_with_gaussian_noise(test_camera):
    geom = TargetGeometry(marker_size_m=0.20)
    obj_pts = geom.get_object_points()
    solver = PnPPoseSolver(PnPConfig(solver="IPPE"))

    true_translation = (0.1, 0.2, 3.0)
    true_rotation = (0.0, 0.0, 0.0)

    proj_corners, _ = SyntheticPoseGenerator.generate(
        test_camera,
        obj_pts,
        true_translation,
        true_rotation,
        noise_std_px=0.5,  # 0.5px noise
    )

    res = solver.solve(obj_pts, proj_corners, test_camera, target_id=1)

    assert res.is_valid is True
    assert res.pose is not None
    assert pytest.approx(res.pose.x, abs=0.05) == 0.1
    assert pytest.approx(res.pose.y, abs=0.05) == 0.2
    assert pytest.approx(res.pose.z, abs=0.08) == 3.0
    assert res.pose.reprojection_error_rms < 2.0


def test_pnp_rejects_shallow_depth(test_camera):
    geom = TargetGeometry(marker_size_m=0.20)
    obj_pts = geom.get_object_points()
    # Set min_depth_m to 5.0m, but target is placed at 2.0m
    solver = PnPPoseSolver(PnPConfig(min_depth_m=5.0))

    true_translation = (0.0, 0.0, 2.0)
    true_rotation = (0.0, 0.0, 0.0)

    proj_corners, _ = SyntheticPoseGenerator.generate(
        test_camera,
        obj_pts,
        true_translation,
        true_rotation,
        noise_std_px=0.0,
    )

    res = solver.solve(obj_pts, proj_corners, test_camera, target_id=1)
    assert res.is_valid is False
    assert "behind or too close" in res.failure_reason


def test_pnp_rejects_excessive_reprojection_error(test_camera):
    geom = TargetGeometry(marker_size_m=0.20)
    obj_pts = geom.get_object_points()
    # Very strict threshold 0.1px with noisy corners 2.0px
    solver = PnPPoseSolver(PnPConfig(max_reprojection_error_px=0.1))

    true_translation = (0.0, 0.0, 2.0)
    true_rotation = (0.0, 0.0, 0.0)

    proj_corners, _ = SyntheticPoseGenerator.generate(
        test_camera,
        obj_pts,
        true_translation,
        true_rotation,
        noise_std_px=2.0,
    )

    res = solver.solve(obj_pts, proj_corners, test_camera, target_id=1)
    assert res.is_valid is False
    assert "Reprojection RMS error" in res.failure_reason



def test_pnp_rejects_insufficient_points(test_camera):
    solver = PnPPoseSolver()
    obj_pts = np.zeros((3, 3))
    img_pts = np.zeros((3, 2))
    res = solver.solve(obj_pts, img_pts, test_camera)
    assert res.is_valid is False
    assert "Insufficient point correspondences" in res.failure_reason
