"""Pinhole camera model, intrinsic calibration validation, and projection utilities."""

import os
from typing import Optional, Tuple, Union
import cv2
import numpy as np
import yaml

from skyvanta.core.config import CameraConfig
from skyvanta.core.exceptions import CalibrationError
from skyvanta.core.types import CameraIntrinsics


class CameraModel:
    """Calibrated pinhole camera model handling coordinate projections and ray casting."""

    def __init__(self, intrinsics: Union[CameraIntrinsics, CameraConfig]):
        if isinstance(intrinsics, CameraConfig):
            self.intrinsics = CameraIntrinsics(
                image_width=intrinsics.image_width,
                image_height=intrinsics.image_height,
                fx=intrinsics.fx,
                fy=intrinsics.fy,
                cx=intrinsics.cx,
                cy=intrinsics.cy,
                distortion_coefficients=intrinsics.distortion_coefficients,
            )
        else:
            self.intrinsics = intrinsics

        self._validate()

        self.matrix_k = np.array([
            [self.intrinsics.fx, 0.0, self.intrinsics.cx],
            [0.0, self.intrinsics.fy, self.intrinsics.cy],
            [0.0, 0.0, 1.0],
        ], dtype=np.float64)

        self.dist_coeffs = np.array(self.intrinsics.distortion_coefficients, dtype=np.float64).reshape(-1, 1)

    def _validate(self) -> None:
        """Validates numerical integrity of intrinsic parameters."""
        if self.intrinsics.image_width <= 0 or self.intrinsics.image_height <= 0:
            raise CalibrationError(
                f"Invalid image dimensions: {self.intrinsics.image_width}x{self.intrinsics.image_height}"
            )
        if self.intrinsics.fx <= 0.0 or self.intrinsics.fy <= 0.0:
            raise CalibrationError(
                f"Focal length must be strictly positive (fx={self.intrinsics.fx}, fy={self.intrinsics.fy})"
            )
        if not (0.0 <= self.intrinsics.cx <= self.intrinsics.image_width):
            raise CalibrationError(
                f"Principal point cx={self.intrinsics.cx} is outside image width [0, {self.intrinsics.image_width}]"
            )
        if not (0.0 <= self.intrinsics.cy <= self.intrinsics.image_height):
            raise CalibrationError(
                f"Principal point cy={self.intrinsics.cy} is outside image height [0, {self.intrinsics.image_height}]"
            )
        if not np.all(np.isfinite(self.intrinsics.distortion_coefficients)):
            raise CalibrationError("Distortion coefficients contain non-finite values")

    @classmethod
    def from_yaml(cls, path: str) -> "CameraModel":
        """Loads camera calibration from a YAML file."""
        if not os.path.isfile(path):
            raise CalibrationError(f"Calibration file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        try:
            intrinsics = CameraIntrinsics(**data)
            return cls(intrinsics)
        except Exception as e:
            raise CalibrationError(f"Failed to parse camera calibration from {path}: {e}")

    def to_yaml(self, path: str) -> None:
        """Saves camera calibration to a YAML file."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.intrinsics.model_dump(), f, default_flow_style=False)

    def project_points(
        self,
        object_points_3d: np.ndarray,
        rvec: np.ndarray,
        tvec: np.ndarray,
    ) -> np.ndarray:
        """Projects 3D object points to 2D image coordinates using camera matrix and distortion.

        Args:
            object_points_3d: (N, 3) array of 3D points in target frame.
            rvec: (3, 1) or (3,) Rodrigues rotation vector.
            tvec: (3, 1) or (3,) Translation vector in meters.

        Returns:
            (N, 2) array of projected pixel coordinates.
        """
        obj_pts = np.ascontiguousarray(object_points_3d, dtype=np.float64).reshape(-1, 1, 3)
        r = np.ascontiguousarray(rvec, dtype=np.float64).reshape(3, 1)
        t = np.ascontiguousarray(tvec, dtype=np.float64).reshape(3, 1)

        proj, _ = cv2.projectPoints(obj_pts, r, t, self.matrix_k, self.dist_coeffs)
        return proj.reshape(-1, 2)

    def undistort_points(self, points_2d: np.ndarray) -> np.ndarray:
        """Undistorts 2D pixel coordinates to ideal pinhole coordinates."""
        pts = np.ascontiguousarray(points_2d, dtype=np.float64).reshape(-1, 1, 2)
        undist = cv2.undistortPoints(pts, self.matrix_k, self.dist_coeffs, P=self.matrix_k)
        return undist.reshape(-1, 2)

    def pixel_to_ray(self, u: float, v: float) -> np.ndarray:
        """Computes normalized unit ray vector in camera optical frame for a given pixel coordinate."""
        x_norm = (u - self.intrinsics.cx) / self.intrinsics.fx
        y_norm = (v - self.intrinsics.cy) / self.intrinsics.fy
        ray = np.array([x_norm, y_norm, 1.0], dtype=np.float64)
        norm = np.linalg.norm(ray)
        return ray / norm if norm > 0 else ray
