"""Synthetic sensor generation (Camera, IMU, Rangefinder) for the Digital Twin."""

from typing import Optional, Tuple
import numpy as np

from skyvanta.core.config import CameraConfig
from skyvanta.core.types import FrameId, IMUMeasurement, LandingTarget, Pose6D, PoseEstimateResult
from skyvanta.spatial.camera import CameraModel
from skyvanta.spatial.transform import (
    rotation_matrix_to_euler,
    rotation_matrix_to_quaternion,
    rotation_matrix_to_rvec,
)


class SyntheticSensorSuite:
    """Generates realistic noisy measurements for camera, IMU, and rangefinder subsystems."""

    def __init__(
        self,
        camera_model: Optional[CameraModel] = None,
        pixel_noise_std: float = 0.5,
        accel_noise_std: float = 0.02,
        gyro_noise_std: float = 0.005,
        random_seed: Optional[int] = 42,
    ):
        self.camera_model = camera_model or CameraModel(
            CameraConfig(image_width=640, image_height=480, fx=800.0, fy=800.0, cx=320.0, cy=240.0)
        )
        self.pixel_noise_std = pixel_noise_std

        self.accel_noise_std = accel_noise_std
        self.gyro_noise_std = gyro_noise_std
        self._rng = np.random.default_rng(random_seed)

        # Static extrinsics: Camera mounted on drone body pointing down
        # Body frame (NED) to Camera optical frame (+X right, +Y down, +Z forward/down)
        self.R_body_to_cam = np.array([
            [0.0, 1.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
        ], dtype=np.float64)

    def generate_pose_estimate(
        self,
        drone_pos_world: np.ndarray,
        drone_R_world: np.ndarray,
        pad_pos_world: np.ndarray,
        t_sec: float,
        is_occluded: bool = False,
        extra_pixel_noise_std: float = 0.0,
    ) -> Optional[PoseEstimateResult]:
        """Generates a synthetic 6-DoF PoseEstimateResult relative to the camera."""
        if is_occluded:
            return None

        # Relative vector in body / camera frame
        dx = pad_pos_world[0] - drone_pos_world[0]
        dy = pad_pos_world[1] - drone_pos_world[1]
        dz = abs(drone_pos_world[2] - pad_pos_world[2])

        if dz < 0.01:
            return None

        # Add Gaussian measurement noise
        total_noise_std = self.pixel_noise_std + extra_pixel_noise_std
        noise = self._rng.normal(0.0, total_noise_std * 0.005, size=3)
        tx_noisy = dx + noise[0]
        ty_noisy = dy + noise[1]
        tz_noisy = dz + noise[2]

        R_target_to_cam = np.eye(3, dtype=np.float64)
        rvec = (0.0, 0.0, 0.0)
        quaternion = (1.0, 0.0, 0.0, 0.0)
        euler_rad = (0.0, 0.0, 0.0)
        euler_deg = (0.0, 0.0, 0.0)
        range_m = float(np.linalg.norm([tx_noisy, ty_noisy, tz_noisy]))
        reproj_rms = float(total_noise_std)

        pose_6d = Pose6D(
            x=float(tx_noisy),
            y=float(ty_noisy),
            z=float(tz_noisy),
            range_m=range_m,
            rotation_matrix=R_target_to_cam.tolist(),
            rvec=rvec,
            quaternion=quaternion,
            euler_deg=euler_deg,
            euler_rad=euler_rad,
            reprojection_error_rms=reproj_rms,
            reprojection_error_max=reproj_rms * 1.5,
            pose_quality=max(0.1, min(1.0, 1.0 - reproj_rms * 0.05)),
            is_valid=True,
            timestamp_sec=max(0.0001, t_sec),
            frame_id=0,
            target_id=1,
        )

        return PoseEstimateResult(
            timestamp_sec=max(0.0001, t_sec),
            frame_id=0,
            target_id=1,
            pose=pose_6d,
            reprojection_error_rms=reproj_rms,
            pose_quality=pose_6d.pose_quality,
            is_valid=True,
        )


    def generate_imu(
        self,
        drone_accel_world: np.ndarray,
        drone_R_world: np.ndarray,
        drone_omega_body: np.ndarray,
        t_sec: float,
        bias_accel: np.ndarray = np.zeros(3),
        bias_gyro: np.ndarray = np.zeros(3),
    ) -> IMUMeasurement:
        """Generates specific force and angular velocity IMU packet."""
        gravity_world = np.array([0.0, 0.0, 9.80665], dtype=np.float64)
        specific_force_world = drone_accel_world - gravity_world
        specific_force_body = drone_R_world.T @ specific_force_world

        noise_accel = self._rng.normal(0.0, self.accel_noise_std, size=3)
        noise_gyro = self._rng.normal(0.0, self.gyro_noise_std, size=3)

        accel_meas = specific_force_body + bias_accel + noise_accel
        gyro_meas = drone_omega_body + bias_gyro + noise_gyro

        return IMUMeasurement(
            timestamp_sec=max(0.0001, t_sec),
            linear_acceleration_m_s2=tuple(float(x) for x in accel_meas),
            angular_velocity_rad_s=tuple(float(x) for x in gyro_meas),
            frame_id=FrameId.BODY,
        )

