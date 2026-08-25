"""Simulated camera sensor with projection, noise, latency, and dropout models."""

from typing import List, Optional, Tuple
import cv2
import numpy as np

from skyvanta.core.config import CameraConfig
from skyvanta.core.types import BoundingBox, Detection, DetectionSource
from skyvanta.simulation.dropout import FrameDropoutModel
from skyvanta.simulation.latency import LatencyModel
from skyvanta.simulation.noise import GaussianNoise
from skyvanta.simulation.target import SimulatedLandingTarget
from skyvanta.spatial.camera import CameraModel
from skyvanta.spatial.transform import (
    quaternion_to_rotation_matrix,
    rotation_matrix_to_quaternion,
    rotation_matrix_to_rvec,
)


class SimulatedCamera:
    """Synthetic camera sensor generating 2D observations from 3D world states."""

    def __init__(
        self,
        camera_model: Optional[CameraModel] = None,
        frame_rate_hz: float = 30.0,
        pixel_noise_sigma: float = 0.5,
        dropout_model: Optional[FrameDropoutModel] = None,
        latency_model: Optional[LatencyModel] = None,
        seed: Optional[int] = None,
    ):
        if camera_model is None:
            config = CameraConfig()
            self.camera_model = CameraModel(config)
        else:
            self.camera_model = camera_model

        self.frame_rate_hz = max(1.0, float(frame_rate_hz))
        self.frame_interval_sec = 1.0 / self.frame_rate_hz
        self.noise = GaussianNoise(mean=0.0, sigma=pixel_noise_sigma, seed=seed)
        self.dropout = dropout_model or FrameDropoutModel()
        self.latency = latency_model or LatencyModel(mean_latency_sec=0.02, seed=seed)

        self._frame_count: int = 0
        self._last_capture_time: float = -1.0

    @property
    def intrinsics(self):
        return self.camera_model.intrinsics

    def capture_target_observation(
        self,
        drone_pos_world: np.ndarray,
        drone_R_world: np.ndarray,
        target: SimulatedLandingTarget,
        current_time_sec: float,
    ) -> Optional[Tuple[np.ndarray, Detection, np.ndarray]]:
        """Simulates camera image capture and returns 2D projected corners and Detection object.

        Returns:
            (projected_corners_2d (4, 2), detection, true_3d_corners_cam) or None if occluded/dropped/out-of-fov.
        """
        # Check frame rate timing
        if self._last_capture_time >= 0.0 and (current_time_sec - self._last_capture_time) < (self.frame_interval_sec * 0.9):
            return None

        self._frame_count += 1
        self._last_capture_time = current_time_sec

        # Check frame dropout
        if self.dropout.should_drop(self._frame_count, current_time_sec):
            return None

        # Check target visibility/occlusion
        if not target.is_visible(current_time_sec):
            return None

        # 1. Transform World Target Corners to Camera Frame
        # Target in world
        pad_corners_world = target.get_3d_corners_world(current_time_sec)  # (4, 3)

        # Camera in world (assuming camera optical axis +Z forward/down, mounted rigidly to body)
        # T_W_C: translation is drone_pos_world, orientation R_W_C
        # For standard downward camera: R_B_C maps Body [X-fwd, Y-right, Z-down] to Camera [X-right, Y-down, Z-forward]
        R_B_C = np.array([
            [0.0, 1.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, -1.0],
        ], dtype=np.float64)

        R_W_C = drone_R_world @ R_B_C
        t_W_C = drone_pos_world

        # Inverse transform: T_C_W = T_W_C^(-1)
        R_C_W = R_W_C.T
        t_C_W = -R_C_W @ t_W_C

        # Transform 3D corners to camera frame: p_C = R_C_W * p_W + t_C_W
        corners_cam = (R_C_W @ pad_corners_world.T).T + t_C_W

        # Check if all points are in front of camera (Z > 0.1m)
        if np.any(corners_cam[:, 2] <= 0.1):
            return None

        # 2. Project 3D points to 2D pixels using CameraModel
        rvec = rotation_matrix_to_rvec(R_C_W)
        tvec = t_C_W

        projected = self.camera_model.project_points(
            object_points_3d=pad_corners_world,
            rvec=rvec,
            tvec=tvec,
        )

        # 3. Add Gaussian Pixel Noise
        noise_samples = self.noise.sample_vec(8).reshape(4, 2)
        noisy_pixels = projected + noise_samples

        # 4. Check Field of View Bounds
        w = self.intrinsics.image_width
        h = self.intrinsics.image_height

        min_u = float(np.min(noisy_pixels[:, 0]))
        max_u = float(np.max(noisy_pixels[:, 0]))
        min_v = float(np.min(noisy_pixels[:, 1]))
        max_v = float(np.max(noisy_pixels[:, 1]))

        if max_u < 0 or min_u > w or max_v < 0 or min_v > h:
            return None  # Out of FOV

        # Formulate Detection Bounding Box
        bbox = BoundingBox(
            x1=max(0.0, min_u),
            y1=max(0.0, min_v),
            x2=min(float(w), max_u),
            y2=min(float(h), max_v),
        )

        detection = Detection(
            bbox=bbox,
            confidence=0.98,
            class_name="landing_pad",
            class_id=target.target_id,
            source=DetectionSource.YOLO,
            timestamp_sec=current_time_sec,
            frame_id=self._frame_count,
        )

        return (noisy_pixels, detection, corners_cam)
