"""Unit tests for camera intrinsic calibration, validation, and projection."""

import pytest
import numpy as np

from skyvanta.core.config import CameraConfig
from skyvanta.core.exceptions import CalibrationError
from skyvanta.core.types import CameraIntrinsics
from skyvanta.spatial.camera import CameraModel


def test_valid_camera_calibration():
    cfg = CameraConfig(
        image_width=1280,
        image_height=720,
        fx=1000.0,
        fy=1000.0,
        cx=640.0,
        cy=360.0,
        distortion_coefficients=[0.0, 0.0, 0.0, 0.0, 0.0],
    )
    cam = CameraModel(cfg)

    assert cam.matrix_k.shape == (3, 3)
    assert cam.matrix_k[0, 0] == 1000.0
    assert cam.matrix_k[1, 1] == 1000.0
    assert cam.matrix_k[0, 2] == 640.0
    assert cam.matrix_k[1, 2] == 360.0


def test_invalid_focal_length():
    # Pydantic validation catches negative fx at config construction
    with pytest.raises(Exception):
        CameraConfig(image_width=640, image_height=480, fx=-500.0, fy=500.0, cx=320.0, cy=240.0)

    # CameraModel validation also catches manually constructed invalid model
    intr = CameraIntrinsics.model_construct(
        image_width=640, image_height=480, fx=-500.0, fy=500.0, cx=320.0, cy=240.0,
        distortion_coefficients=[0.0, 0.0, 0.0, 0.0, 0.0]
    )
    with pytest.raises(CalibrationError, match="Focal length must be strictly positive"):
        CameraModel(intr)


def test_invalid_principal_point():
    cfg = CameraConfig(image_width=640, image_height=480, fx=500.0, fy=500.0, cx=800.0, cy=240.0)
    with pytest.raises(CalibrationError, match="Principal point cx=800.0 is outside"):
        CameraModel(cfg)


def test_invalid_image_dimensions():
    with pytest.raises(Exception):
        CameraConfig(image_width=0, image_height=480, fx=500.0, fy=500.0, cx=0.0, cy=240.0)

    intr = CameraIntrinsics.model_construct(
        image_width=0, image_height=480, fx=500.0, fy=500.0, cx=0.0, cy=240.0,
        distortion_coefficients=[0.0, 0.0, 0.0, 0.0, 0.0]
    )
    with pytest.raises(CalibrationError, match="Invalid image dimensions"):
        CameraModel(intr)



def test_invalid_distortion_coefficients():
    cfg = CameraConfig(
        image_width=640,
        image_height=480,
        fx=500.0,
        fy=500.0,
        cx=320.0,
        cy=240.0,
        distortion_coefficients=[0.0, float("nan"), 0.0, 0.0, 0.0],
    )
    with pytest.raises(CalibrationError, match="Distortion coefficients contain non-finite"):
        CameraModel(cfg)


def test_pixel_to_ray_and_projection():
    cfg = CameraConfig(image_width=1280, image_height=720, fx=1000.0, fy=1000.0, cx=640.0, cy=360.0)
    cam = CameraModel(cfg)

    # Principal point ray should point directly along +Z axis [0, 0, 1]
    ray_center = cam.pixel_to_ray(640.0, 360.0)
    assert pytest.approx(ray_center[0], abs=1e-5) == 0.0
    assert pytest.approx(ray_center[1], abs=1e-5) == 0.0
    assert pytest.approx(ray_center[2], abs=1e-5) == 1.0

    # Project a 3D point at (0, 0, 5.0) in front of camera
    obj_pt = np.array([[0.0, 0.0, 0.0]])
    rvec = np.zeros(3)
    tvec = np.array([0.0, 0.0, 5.0])
    proj = cam.project_points(obj_pt, rvec, tvec)
    assert pytest.approx(proj[0, 0], abs=1e-3) == 640.0
    assert pytest.approx(proj[0, 1], abs=1e-3) == 360.0
