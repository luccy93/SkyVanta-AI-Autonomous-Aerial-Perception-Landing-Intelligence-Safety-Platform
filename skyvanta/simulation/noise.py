"""Deterministic noise models for sensor and state perturbations."""

from typing import Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field


class GaussianNoise:
    """Deterministic Gaussian white noise generator with reproducible RNG seeding."""

    def __init__(self, mean: float = 0.0, sigma: float = 1.0, seed: Optional[int] = None):
        self.mean = float(mean)
        self.sigma = float(sigma)
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def sample(self) -> float:
        """Returns a single scalar Gaussian noise sample."""
        if self.sigma <= 0.0:
            return self.mean
        return float(self._rng.normal(self.mean, self.sigma))

    def sample_vec(self, size: int) -> np.ndarray:
        """Returns a 1D vector of Gaussian noise samples."""
        if self.sigma <= 0.0:
            return np.full(size, self.mean, dtype=np.float64)
        return self._rng.normal(self.mean, self.sigma, size=size).astype(np.float64)

    def reset(self, seed: Optional[int] = None) -> None:
        """Resets the random number generator."""
        if seed is not None:
            self.seed = seed
        self._rng = np.random.default_rng(self.seed)


class BiasNoise:
    """Deterministic constant bias offset with optional random initialization."""

    def __init__(self, bias: float = 0.0, seed: Optional[int] = None):
        self.bias = float(bias)
        self.seed = seed

    def sample(self) -> float:
        """Returns the constant bias value."""
        return self.bias

    def sample_vec(self, size: int) -> np.ndarray:
        """Returns a vector filled with the constant bias."""
        return np.full(size, self.bias, dtype=np.float64)


class RandomWalkNoise:
    """Brownian random walk drift noise generator."""

    def __init__(self, drift_rate: float = 0.001, initial_value: float = 0.0, seed: Optional[int] = None):
        self.drift_rate = float(drift_rate)
        self.current_value = float(initial_value)
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def step(self, dt_sec: float) -> float:
        """Advances the random walk by dt_sec and returns the updated state."""
        if self.drift_rate > 0.0 and dt_sec > 0.0:
            step_sigma = self.drift_rate * np.sqrt(dt_sec)
            self.current_value += float(self._rng.normal(0.0, step_sigma))
        return self.current_value

    def sample(self) -> float:
        """Returns the current accumulated drift value."""
        return self.current_value

    def reset(self, initial_value: float = 0.0, seed: Optional[int] = None) -> None:
        """Resets the drift state."""
        if seed is not None:
            self.seed = seed
        self._rng = np.random.default_rng(self.seed)
        self.current_value = float(initial_value)


class UniformNoise:
    """Deterministic bounded uniform noise generator."""

    def __init__(self, low: float = -1.0, high: float = 1.0, seed: Optional[int] = None):
        self.low = float(low)
        self.high = float(high)
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def sample(self) -> float:
        """Returns a single uniform random sample in [low, high]."""
        return float(self._rng.uniform(self.low, self.high))

    def sample_vec(self, size: int) -> np.ndarray:
        """Returns a vector of uniform random samples."""
        return self._rng.uniform(self.low, self.high, size=size).astype(np.float64)

    def reset(self, seed: Optional[int] = None) -> None:
        """Resets the random number generator."""
        if seed is not None:
            self.seed = seed
        self._rng = np.random.default_rng(self.seed)


class SensorNoiseConfig(BaseModel):
    """Declarative configuration parameters for all simulated sensor noise sources."""
    camera_pixel_sigma: float = Field(default=0.5, ge=0.0, description="Camera corner detection pixel noise std dev")
    imu_accel_sigma: float = Field(default=0.05, ge=0.0, description="IMU accelerometer noise std dev in m/s²")
    imu_gyro_sigma: float = Field(default=0.005, ge=0.0, description="IMU gyroscope noise std dev in rad/s")
    imu_accel_bias: Tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0), description="Constant accelerometer bias [bx, by, bz] in m/s²")
    imu_gyro_bias: Tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0), description="Constant gyroscope bias [bgx, bgy, bgz] in rad/s")
    imu_accel_drift_rate: float = Field(default=0.0001, ge=0.0, description="Accelerometer bias random walk rate in m/s²/sqrt(s)")
    imu_gyro_drift_rate: float = Field(default=0.00001, ge=0.0, description="Gyroscope bias random walk rate in rad/s/sqrt(s)")
    pose_position_sigma: float = Field(default=0.02, ge=0.0, description="PnP position estimation noise std dev in meters")
    pose_orientation_sigma: float = Field(default=0.01, ge=0.0, description="PnP orientation angle noise std dev in radians")
    random_seed: Optional[int] = Field(default=42, description="Base random seed for reproducible noise generation")
