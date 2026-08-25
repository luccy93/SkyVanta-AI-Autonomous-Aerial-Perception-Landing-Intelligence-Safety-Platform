"""Engineering vehicle disturbance models for software validation."""

from typing import List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field


class DisturbanceEvent(BaseModel):
    """Discrete temporal disturbance applied to vehicle states."""
    timestamp_sec: float
    duration_sec: float = 0.0
    lateral_force_mps2: Tuple[float, float] = (0.0, 0.0)
    vertical_force_mps2: float = 0.0
    velocity_impulse_mps: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    position_offset_m: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation_disturbance_deg: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_rate_disturbance_rad_s: Tuple[float, float, float] = (0.0, 0.0, 0.0)


class DisturbanceModel:
    """Manages scheduled engineering disturbances on the simulated vehicle."""

    def __init__(self, constant_wind_mps: Tuple[float, float, float] = (0.0, 0.0, 0.0)):
        self.constant_wind_mps = np.array(constant_wind_mps, dtype=np.float64)
        self._events: List[DisturbanceEvent] = []
        self._applied_impulses: set = set()

    def add_event(self, event: DisturbanceEvent) -> None:
        """Schedules a disturbance event."""
        self._events.append(event)

    def get_net_acceleration_disturbance(self, current_time_sec: float) -> np.ndarray:
        """Computes net acceleration disturbance [ax, ay, az] in World frame at current_time_sec."""
        accel = np.zeros(3, dtype=np.float64)
        for event in self._events:
            end_t = event.timestamp_sec + max(0.001, event.duration_sec)
            if event.timestamp_sec <= current_time_sec <= end_t:
                accel[0] += event.lateral_force_mps2[0]
                accel[1] += event.lateral_force_mps2[1]
                accel[2] += event.vertical_force_mps2
        return accel

    def check_velocity_impulse(self, current_time_sec: float, dt_sec: float) -> np.ndarray:
        """Returns any one-time velocity impulse triggering in [current_time_sec, current_time_sec + dt_sec]."""
        dv = np.zeros(3, dtype=np.float64)
        for idx, event in enumerate(self._events):
            if idx not in self._applied_impulses:
                if current_time_sec <= event.timestamp_sec < (current_time_sec + dt_sec):
                    dv += np.array(event.velocity_impulse_mps, dtype=np.float64)
                    self._applied_impulses.add(idx)
        return dv

    def get_angular_disturbance(self, current_time_sec: float) -> np.ndarray:
        """Computes net body angular rate disturbance [wx, wy, wz] in rad/s."""
        omega_dist = np.zeros(3, dtype=np.float64)
        for event in self._events:
            end_t = event.timestamp_sec + max(0.001, event.duration_sec)
            if event.timestamp_sec <= current_time_sec <= end_t:
                omega_dist += np.array(event.angular_rate_disturbance_rad_s, dtype=np.float64)
        return omega_dist

    def clear(self) -> None:
        """Clears all scheduled events."""
        self._events.clear()
        self._applied_impulses.clear()
