"""Deterministic synthetic 6-DoF pose and 2D projection generator for offline testing."""

import math
from typing import Optional, Tuple, Union
import numpy as np

from skyvanta.core.types import Pose6D
from skyvanta.spatial.camera import CameraModel
from skyvanta.spatial.transform import (
    euler_to_rotation_matrix,
    rotation_matrix_to_euler,
    rotation_matrix_to_quaternion,
    rotation_matrix_to_rvec,
    rvec_to_rotation_matrix,
)


class SyntheticPoseGenerator:
    """Generates ground-truth 6-DoF poses and reprojected 2D pixel corners with controlled noise."""

    @staticmethod
    def generate(
        camera_model: CameraModel,
        object_points_3d: np.ndarray,
        translation_m: Tuple[float, float, float],
        rotation: Union[Tuple[float, float, float], np.ndarray],  # (roll_rad, pitch_rad, yaw_rad) or rvec or 3x3 R
        noise_std_px: float = 0.0,
        random_seed: Optional[int] = 42,
    ) -> Tuple[np.ndarray, Pose6D]:
        """Projects known 3D object points to 2D image coordinates with optional controlled Gaussian noise.

        Args:
            camera_model: Calibrated CameraModel.
            object_points_3d: (N, 3) 3D coordinates in target frame.
            translation_m: True translation (tx, ty, tz) in meters.
            rotation: True rotation as Euler angles in radians (roll, pitch, yaw), Rodrigues rvec (3,), or 3x3 matrix.
            noise_std_px: Standard deviation of additive Gaussian pixel noise (0.0 = zero noise).
            random_seed: Random seed for deterministic reproducibility.

        Returns:
            (projected_image_points_2d, true_pose_6d)
        """
        tx, ty, tz = translation_m
        tvec = np.array([tx, ty, tz], dtype=np.float64)

        if isinstance(rotation, np.ndarray) and rotation.shape == (3, 3):
            R_mat = rotation
            rvec = rotation_matrix_to_rvec(R_mat)
        elif isinstance(rotation, np.ndarray) and rotation.size == 3:
            rvec = rotation.flatten()
            R_mat = rvec_to_rotation_matrix(rvec)
        elif isinstance(rotation, (tuple, list)) and len(rotation) == 3:
            roll, pitch, yaw = rotation
            R_mat = euler_to_rotation_matrix(roll, pitch, yaw)
            rvec = rotation_matrix_to_rvec(R_mat)
        else:
            raise ValueError(f"Unsupported rotation format: {rotation}")

        # Project 3D object points to 2D image plane
        projected = camera_model.project_points(object_points_3d, rvec, tvec)

        if noise_std_px > 0.0:
            rng = np.random.default_rng(random_seed)
            noise = rng.normal(0.0, noise_std_px, size=projected.shape)
            projected = projected + noise

        quat = rotation_matrix_to_quaternion(R_mat)
        euler_rad, euler_deg = rotation_matrix_to_euler(R_mat)
        range_m = float(math.sqrt(tx * tx + ty * ty + tz * tz))

        true_pose = Pose6D(
            x=float(tx),
            y=float(ty),
            z=float(tz),
            rotation_matrix=R_mat.tolist(),
            rvec=(float(rvec[0]), float(rvec[1]), float(rvec[2])),
            quaternion=quat,
            euler_deg=euler_deg,
            euler_rad=euler_rad,
            range_m=range_m,
            reprojection_error_rms=0.0,
            reprojection_error_max=0.0,
            pose_quality=1.0,
            is_valid=True,
            timestamp_sec=0.0,
            frame_id=0,
            target_id=0,
            solver_method="GROUND_TRUTH",
        )

        return projected, true_pose
