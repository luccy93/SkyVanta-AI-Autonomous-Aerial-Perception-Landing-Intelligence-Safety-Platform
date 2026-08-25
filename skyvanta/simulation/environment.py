"""Environmental conditions, wind/gust models, and dynamic landing pad representations."""

import math
from typing import List, Optional, Tuple
import numpy as np


class EnvironmentalConditions:
    """Simulates atmospheric wind, turbulence gusts, lighting, and visual visibility."""

    def __init__(
        self,
        base_wind_mps: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        gust_amplitude_mps: float = 0.0,
        gust_frequency_hz: float = 0.2,
        visibility_factor: float = 1.0,
        random_seed: Optional[int] = 42,
    ):
        self.base_wind = np.array(base_wind_mps, dtype=np.float64)
        self.gust_amplitude = gust_amplitude_mps
        self.gust_frequency = gust_frequency_hz
        self.visibility_factor = max(0.0, min(1.0, visibility_factor))
        self._rng = np.random.default_rng(random_seed)

    def get_wind_at(self, t_sec: float) -> np.ndarray:
        """Computes instantaneous wind velocity vector [wx, wy, wz] at time t."""
        if self.gust_amplitude <= 0.0:
            return self.base_wind.copy()

        # Sinusoidal gust + low-amplitude stochastic noise
        gust_scale = math.sin(2.0 * math.pi * self.gust_frequency * t_sec)
        noise = self._rng.normal(0.0, 0.1 * self.gust_amplitude, size=3)
        gust = np.array([gust_scale, 0.5 * gust_scale, 0.2 * gust_scale]) * self.gust_amplitude + noise
        return self.base_wind + gust


class LandingPadModel:
    """Represents a static or moving landing pad in the WORLD coordinate frame."""

    def __init__(
        self,
        initial_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        velocity_mps: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        marker_size_m: float = 0.20,
        marker_id: int = 1,
    ):
        self.position = np.array(initial_position, dtype=np.float64)
        self.velocity = np.array(velocity_mps, dtype=np.float64)
        self.marker_size_m = marker_size_m
        self.marker_id = marker_id
        self.rotation_matrix = np.eye(3, dtype=np.float64)

    def get_position_at(self, t_sec: float) -> np.ndarray:
        """Calculates pad position at timestamp t."""
        return self.position + self.velocity * t_sec

    def get_3d_corners(self, t_sec: float) -> np.ndarray:
        """Returns 4 object corner coordinates (N, 3) in WORLD frame at time t."""
        s = self.marker_size_m / 2.0
        # Local corners in pad coordinate system (z=0)
        local_corners = np.array([
            [-s, -s, 0.0],
            [ s, -s, 0.0],
            [ s,  s, 0.0],
            [-s,  s, 0.0],
        ], dtype=np.float64)

        pos = self.get_position_at(t_sec)
        world_corners = (self.rotation_matrix @ local_corners.T).T + pos
        return world_corners
