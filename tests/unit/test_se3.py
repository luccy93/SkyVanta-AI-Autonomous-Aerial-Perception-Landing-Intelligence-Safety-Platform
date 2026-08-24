"""Unit tests for SE(3) spatial transformations, composition, inversion, and point transforms."""

import math
import pytest
import numpy as np

from skyvanta.core.exceptions import InvalidTransformError
from skyvanta.core.types import FrameId, Pose6D
from skyvanta.spatial.se3 import SE3Transform
from skyvanta.spatial.transform import euler_to_rotation_matrix


def test_se3_identity():
    t_id = SE3Transform.identity(FrameId.BODY)
    assert t_id.source_frame == FrameId.BODY
    assert t_id.target_frame == FrameId.BODY
    assert np.allclose(t_id.rotation_matrix, np.eye(3))
    assert np.allclose(t_id.translation, np.zeros(3))
    assert np.allclose(t_id.to_matrix(), np.eye(4))


def test_se3_validation_rejections():
    # Non-finite translation
    with pytest.raises(InvalidTransformError, match="non-finite"):
        SE3Transform(
            source_frame=FrameId.CAMERA,
            target_frame=FrameId.BODY,
            translation=[float("nan"), 0.0, 1.0],
        )

    # Non-orthonormal rotation (scaled matrix)
    scaled_R = np.eye(3) * 2.0
    with pytest.raises(InvalidTransformError, match="violates SO\\(3\\) orthonormality"):
        SE3Transform(
            source_frame=FrameId.CAMERA,
            target_frame=FrameId.BODY,
            rotation=scaled_R,
        )

    # Reflection matrix (det = -1)
    reflection_R = np.diag([1.0, 1.0, -1.0])
    with pytest.raises(InvalidTransformError, match="proper rotation"):
        SE3Transform(
            source_frame=FrameId.CAMERA,
            target_frame=FrameId.BODY,
            rotation=reflection_R,
        )


def test_se3_inverse():
    R = euler_to_rotation_matrix(math.radians(20.0), math.radians(-15.0), math.radians(45.0))
    t = np.array([1.5, -2.0, 3.5])
    transform = SE3Transform(
        source_frame=FrameId.CAMERA,
        target_frame=FrameId.BODY,
        rotation=R,
        translation=t,
    )

    t_inv = transform.inverse()
    assert t_inv.source_frame == FrameId.BODY
    assert t_inv.target_frame == FrameId.CAMERA

    # Check T * T_inv ≈ I and T_inv * T ≈ I
    mat = transform.to_matrix()
    mat_inv = t_inv.to_matrix()
    assert np.allclose(mat @ mat_inv, np.eye(4), atol=1e-6)
    assert np.allclose(mat_inv @ mat, np.eye(4), atol=1e-6)


def test_se3_composition():
    # T_body_cam
    R1 = euler_to_rotation_matrix(0.0, math.radians(45.0), 0.0)
    t1 = np.array([0.2, 0.0, -0.1])
    t_body_cam = SE3Transform(
        source_frame=FrameId.CAMERA,
        target_frame=FrameId.BODY,
        rotation=R1,
        translation=t1,
    )

    # T_cam_pad
    R2 = euler_to_rotation_matrix(math.radians(10.0), 0.0, 0.0)
    t2 = np.array([0.0, 0.0, 2.0])
    t_cam_pad = SE3Transform(
        source_frame=FrameId.LANDING_PAD,
        target_frame=FrameId.CAMERA,
        rotation=R2,
        translation=t2,
    )

    # T_body_pad = T_body_cam * T_cam_pad
    t_body_pad = t_body_cam.compose(t_cam_pad)
    assert t_body_pad.source_frame == FrameId.LANDING_PAD
    assert t_body_pad.target_frame == FrameId.BODY

    # Compare against homogeneous 4x4 matrix multiplication
    expected_mat = t_body_cam.to_matrix() @ t_cam_pad.to_matrix()
    assert np.allclose(t_body_pad.to_matrix(), expected_mat, atol=1e-6)


def test_se3_associativity():
    # 3 transforms: A -> B -> C -> D
    t_a_b = SE3Transform.from_euler(
        source_frame="CUSTOM", target_frame=FrameId.LANDING_PAD,
        translation=(0.1, 0.2, 0.3), euler_deg=(10.0, 20.0, 30.0)
    )
    t_b_c = SE3Transform.from_euler(
        source_frame=FrameId.LANDING_PAD, target_frame=FrameId.CAMERA,
        translation=(0.0, 0.0, 1.5), euler_deg=(0.0, -15.0, 5.0)
    )
    t_c_d = SE3Transform.from_euler(
        source_frame=FrameId.CAMERA, target_frame=FrameId.BODY,
        translation=(0.2, 0.0, -0.1), euler_deg=(0.0, 45.0, 0.0)
    )

    left_assoc = (t_c_d @ t_b_c) @ t_a_b
    right_assoc = t_c_d @ (t_b_c @ t_a_b)

    assert np.allclose(left_assoc.to_matrix(), right_assoc.to_matrix(), atol=1e-6)


def test_se3_point_and_points_transformation():
    R = euler_to_rotation_matrix(0.0, 0.0, math.radians(90.0))  # 90 deg yaw
    t = np.array([1.0, 2.0, 3.0])
    transform = SE3Transform(
        source_frame=FrameId.LANDING_PAD,
        target_frame=FrameId.BODY,
        rotation=R,
        translation=t,
    )

    # Point [1, 0, 0] rotated 90 deg around Z is [0, 1, 0], translated by [1, 2, 3] -> [1, 3, 3]
    p = np.array([1.0, 0.0, 0.0])
    p_trans = transform.transform_point(p)
    assert np.allclose(p_trans, [1.0, 3.0, 3.0], atol=1e-5)

    # Array of points
    points = np.array([
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ])
    pts_trans = transform.transform_points(points)
    assert pts_trans.shape == (2, 3)
    assert np.allclose(pts_trans[0], [1.0, 3.0, 3.0], atol=1e-5)
    # [0, 1, 0] rotated 90 deg is [-1, 0, 0] + [1, 2, 3] -> [0, 2, 3]
    assert np.allclose(pts_trans[1], [0.0, 2.0, 3.0], atol=1e-5)


def test_se3_pose_transformation():
    # Transform camera pose to body pose
    t_body_cam = SE3Transform.from_euler(
        source_frame=FrameId.CAMERA,
        target_frame=FrameId.BODY,
        translation=(0.20, 0.0, -0.10),
        euler_deg=(0.0, 0.0, 0.0),
    )

    cam_pose = Pose6D(
        x=0.0, y=0.0, z=2.0,
        rotation_matrix=np.eye(3).tolist(),
        rvec=(0.0, 0.0, 0.0),
        quaternion=(1.0, 0.0, 0.0, 0.0),
        euler_deg=(0.0, 0.0, 0.0),
        euler_rad=(0.0, 0.0, 0.0),
        range_m=2.0,
        reprojection_error_rms=0.2,
        reprojection_error_max=0.2,
        pose_quality=0.95,
        is_valid=True,
        timestamp_sec=1.0,
        frame_id=5,
        target_id=1,
        solver_method="IPPE",
    )

    body_pose = t_body_cam.transform_pose(cam_pose)
    assert body_pose.x == pytest.approx(0.20, abs=1e-4)
    assert body_pose.y == pytest.approx(0.0, abs=1e-4)
    assert body_pose.z == pytest.approx(1.90, abs=1e-4)
    assert body_pose.reprojection_error_rms == 0.2
