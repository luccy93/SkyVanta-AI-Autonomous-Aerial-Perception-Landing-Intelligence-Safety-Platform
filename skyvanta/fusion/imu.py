from typing import Optional
import numpy as np


from skyvanta.core.config import GravityConfig
from skyvanta.core.exceptions import SensorTimingError
from skyvanta.core.types import IMUMeasurement


class GravityModel:
    """Configurable gravitational acceleration vector in World navigation frame."""

    def __init__(self, config: Optional[GravityConfig] = None):
        cfg = config or GravityConfig()
        direction = np.array(cfg.direction, dtype=np.float64).flatten()
        norm = np.linalg.norm(direction)
        unit_dir = direction / norm if norm > 0 else np.array([0.0, 0.0, 1.0])
        self.vector = unit_dir * cfg.magnitude_m_s2

    @property
    def gravity_vector(self) -> np.ndarray:
        """Returns (3,) gravitational acceleration vector in World frame (m/s²)."""
        return self.vector.copy()


class IMUPreprocessor:
    """Validates IMU timestamp ordering, delta-t intervals, and finite numerical values."""

    def __init__(self, min_dt_sec: float = 0.0001, max_dt_sec: float = 0.10):
        self.min_dt_sec = min_dt_sec
        self.max_dt_sec = max_dt_sec
        self._last_timestamp: Optional[float] = None

    def validate_and_compute_dt(self, measurement: IMUMeasurement) -> float:
        """Validates incoming IMU measurement and computes positive time delta dt."""
        t = measurement.timestamp_sec

        w = np.array(measurement.angular_velocity_rad_s)
        a = np.array(measurement.linear_acceleration_m_s2)

        if not np.all(np.isfinite(w)) or not np.all(np.isfinite(a)):
            raise ValueError(f"IMU measurement contains non-finite values: w={w}, a={a}")

        if self._last_timestamp is None:
            self._last_timestamp = t
            return 0.01  # Default nominal dt for the first sample (100 Hz)

        dt = t - self._last_timestamp
        if dt <= self.min_dt_sec:
            raise SensorTimingError(
                f"Duplicate or backwards IMU timestamp detected (dt={dt:.6f}s <= {self.min_dt_sec:.6f}s)"
            )
        if dt > self.max_dt_sec:
            raise SensorTimingError(
                f"Excessive IMU time gap detected (dt={dt:.6f}s > max {self.max_dt_sec:.6f}s)"
            )

        self._last_timestamp = t
        return float(dt)

    def reset(self) -> None:
        """Resets timestamp tracking history."""
        self._last_timestamp = None
