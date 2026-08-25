"""Synthetic IMU sensor simulation producing strongly typed IMUMeasurements."""

from typing import Optional, Tuple
import numpy as np

from skyvanta.core.types import FrameId, IMUMeasurement
from skyvanta.simulation.dropout import FrameDropoutModel
from skyvanta.simulation.noise import GaussianNoise, RandomWalkNoise


class SimulatedIMU:
    """Generates synthetic 6-DoF inertial measurements (accelerometer & gyroscope)."""

    def __init__(
        self,
        rate_hz: float = 100.0,
        accel_noise_sigma: float = 0.05,
        gyro_noise_sigma: float = 0.005,
        accel_bias: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        gyro_bias: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        accel_drift_rate: float = 0.0001,
        gyro_drift_rate: float = 0.00001,
        accel_scale_error: float = 1.0,
        gyro_scale_error: float = 1.0,
        timestamp_jitter_sigma: float = 0.0,
        dropout_model: Optional[FrameDropoutModel] = None,
        seed: Optional[int] = None,
    ):
        self.rate_hz = max(1.0, float(rate_hz))
        self.dt_sec = 1.0 / self.rate_hz
        self.accel_noise = GaussianNoise(mean=0.0, sigma=accel_noise_sigma, seed=seed)
        self.gyro_noise = GaussianNoise(mean=0.0, sigma=gyro_noise_sigma, seed=(seed + 1 if seed is not None else None))

        self.accel_bias = np.array(accel_bias, dtype=np.float64)
        self.gyro_bias = np.array(gyro_bias, dtype=np.float64)

        self.accel_drift = [RandomWalkNoise(drift_rate=accel_drift_rate, seed=seed) for _ in range(3)]
        self.gyro_drift = [RandomWalkNoise(drift_rate=gyro_drift_rate, seed=seed) for _ in range(3)]

        self.accel_scale_error = float(accel_scale_error)
        self.gyro_scale_error = float(gyro_scale_error)
        self.jitter = GaussianNoise(mean=0.0, sigma=timestamp_jitter_sigma, seed=seed)
        self.dropout = dropout_model or FrameDropoutModel()

        self._sample_count: int = 0
        self._last_sample_time: float = -1.0

    def generate_measurement(
        self,
        drone_accel_world: np.ndarray,
        drone_R_world: np.ndarray,
        drone_omega_body: np.ndarray,
        current_time_sec: float,
        dt_step_sec: float = 0.01,
    ) -> Optional[IMUMeasurement]:
        """Generates an IMUMeasurement packet.

        Specific force in Body frame: a_B = R_BW * (a_W - g_W)
        where g_W = [0, 0, -9.81] m/s².
        """
        self._sample_count += 1

        # Check dropout
        if self.dropout.should_drop(self._sample_count, current_time_sec):
            return None

        # Advance bias random walk
        for d in self.accel_drift:
            d.step(dt_step_sec)
        for d in self.gyro_drift:
            d.step(dt_step_sec)

        # 1. Ideal Specific Force in Body Frame
        g_world = np.array([0.0, 0.0, 9.80665], dtype=np.float64)
        specific_force_world = drone_accel_world - g_world
        # R_BW = R_WB^T
        specific_force_body = drone_R_world.T @ specific_force_world

        # 2. Add Scale, Bias, Drift, and Gaussian Noise
        accel_drift_vec = np.array([d.sample() for d in self.accel_drift])
        accel_noise_vec = self.accel_noise.sample_vec(3)
        meas_accel = (
            specific_force_body * self.accel_scale_error
            + self.accel_bias
            + accel_drift_vec
            + accel_noise_vec
        )

        # 3. Gyroscope Measurement
        gyro_drift_vec = np.array([d.sample() for d in self.gyro_drift])
        gyro_noise_vec = self.gyro_noise.sample_vec(3)
        meas_gyro = (
            drone_omega_body * self.gyro_scale_error
            + self.gyro_bias
            + gyro_drift_vec
            + gyro_noise_vec
        )

        # Timestamp jitter (must be strictly positive for pydantic gt=0.0 constraint)
        jitter_val = self.jitter.sample()
        meas_time = max(0.0001, current_time_sec + jitter_val)

        return IMUMeasurement(
            timestamp_sec=meas_time,
            angular_velocity_rad_s=tuple(float(x) for x in meas_gyro),
            linear_acceleration_m_s2=tuple(float(x) for x in meas_accel),
            frame_id=FrameId.BODY,
        )
