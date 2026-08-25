"""Sensor dropout, frame loss, fault injection, and target occlusion models."""

from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
from pydantic import BaseModel, Field


class FrameDropoutType(str, Enum):
    NONE = "NONE"
    DETERMINISTIC = "DETERMINISTIC"
    PERIODIC = "PERIODIC"
    RANDOM = "RANDOM"
    BURST = "BURST"


class FrameDropoutModel:
    """Simulates deterministic and stochastic frame loss patterns in visual sensors."""

    def __init__(
        self,
        dropout_type: FrameDropoutType = FrameDropoutType.NONE,
        drop_indices: Optional[List[int]] = None,
        drop_period: int = 100,
        drop_burst_length: int = 5,
        drop_probability: float = 0.0,
        burst_start_frame: int = 0,
        seed: Optional[int] = None,
    ):
        self.dropout_type = dropout_type
        self.drop_indices: Set[int] = set(drop_indices or [])
        self.drop_period = max(1, drop_period)
        self.drop_burst_length = max(0, drop_burst_length)
        self.drop_probability = min(1.0, max(0.0, float(drop_probability)))
        self.burst_start_frame = burst_start_frame
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def should_drop(self, frame_index: int, timestamp_sec: float = 0.0) -> bool:
        """Evaluates whether the specified frame should be dropped."""
        if self.dropout_type == FrameDropoutType.NONE:
            return False

        if self.dropout_type == FrameDropoutType.DETERMINISTIC:
            return frame_index in self.drop_indices

        if self.dropout_type == FrameDropoutType.PERIODIC:
            cycle_pos = frame_index % self.drop_period
            return cycle_pos < self.drop_burst_length

        if self.dropout_type == FrameDropoutType.RANDOM:
            return float(self._rng.uniform(0.0, 1.0)) < self.drop_probability

        if self.dropout_type == FrameDropoutType.BURST:
            return self.burst_start_frame <= frame_index < (self.burst_start_frame + self.drop_burst_length)

        return False

    def reset(self, seed: Optional[int] = None) -> None:
        """Resets the random generator state."""
        if seed is not None:
            self.seed = seed
        self._rng = np.random.default_rng(self.seed)


class SensorType(str, Enum):
    CAMERA = "CAMERA"
    IMU = "IMU"
    POSE = "POSE"
    TELEMETRY = "TELEMETRY"
    AUTOPILOT = "AUTOPILOT"


class SensorFaultType(str, Enum):
    NONE = "NONE"
    DROP = "DROP"
    STALE = "STALE"
    NOISY = "NOISY"
    BIAS = "BIAS"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    INVALID = "INVALID"
    DELAYED = "DELAYED"


class ActiveFault(BaseModel):
    """Active fault description with temporal start/end boundaries."""
    fault_type: SensorFaultType
    sensor_type: SensorType
    start_time_sec: float
    end_time_sec: float
    parameters: Dict[str, Any] = Field(default_factory=dict)


class SensorFaultModel:
    """Generic multi-sensor fault injection model."""

    def __init__(self):
        self._faults: List[ActiveFault] = []
        self._stale_cache: Dict[SensorType, Any] = {}

    def add_fault(
        self,
        sensor_type: SensorType,
        fault_type: SensorFaultType,
        start_time_sec: float,
        end_time_sec: float,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Schedules a sensor fault over a temporal interval [start_time_sec, end_time_sec]."""
        self._faults.append(ActiveFault(
            fault_type=fault_type,
            sensor_type=sensor_type,
            start_time_sec=start_time_sec,
            end_time_sec=end_time_sec,
            parameters=parameters or {},
        ))

    def get_active_fault(self, sensor_type: SensorType, current_time_sec: float) -> Optional[ActiveFault]:
        """Returns the first active fault matching sensor_type at current_time_sec, or None."""
        for fault in self._faults:
            if fault.sensor_type == sensor_type and fault.start_time_sec <= current_time_sec <= fault.end_time_sec:
                return fault
        return None

    def update_cache(self, sensor_type: SensorType, data: Any) -> None:
        """Updates last known valid sample for stale fault injection."""
        self._stale_cache[sensor_type] = data

    def get_stale(self, sensor_type: SensorType) -> Optional[Any]:
        """Returns the cached stale sample."""
        return self._stale_cache.get(sensor_type)

    def clear(self) -> None:
        """Clears all scheduled faults."""
        self._faults.clear()
        self._stale_cache.clear()


class OcclusionType(str, Enum):
    NONE = "NONE"
    TEMPORARY = "TEMPORARY"
    PROLONGED = "PROLONGED"
    PERIODIC = "PERIODIC"
    RANDOM = "RANDOM"
    FULL_DISAPPEARANCE = "FULL_DISAPPEARANCE"


class OcclusionModel:
    """Simulates visual landing target occlusions and line-of-sight dropouts."""

    def __init__(
        self,
        occlusion_type: OcclusionType = OcclusionType.NONE,
        start_time_sec: float = 0.0,
        duration_sec: float = 0.0,
        period_sec: float = 5.0,
        duty_cycle: float = 0.5,
        random_probability: float = 0.0,
        seed: Optional[int] = None,
    ):
        self.occlusion_type = occlusion_type
        self.start_time_sec = float(start_time_sec)
        self.duration_sec = float(duration_sec)
        self.period_sec = max(0.1, float(period_sec))
        self.duty_cycle = min(1.0, max(0.0, float(duty_cycle)))
        self.random_probability = min(1.0, max(0.0, float(random_probability)))
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def is_occluded(self, current_time_sec: float) -> bool:
        """Checks if the landing target is currently occluded at current_time_sec."""
        if self.occlusion_type == OcclusionType.NONE:
            return False

        if self.occlusion_type == OcclusionType.TEMPORARY or self.occlusion_type == OcclusionType.PROLONGED:
            return self.start_time_sec <= current_time_sec <= (self.start_time_sec + self.duration_sec)

        if self.occlusion_type == OcclusionType.FULL_DISAPPEARANCE:
            return current_time_sec >= self.start_time_sec

        if self.occlusion_type == OcclusionType.PERIODIC:
            if current_time_sec < self.start_time_sec:
                return False
            cycle_t = (current_time_sec - self.start_time_sec) % self.period_sec
            return cycle_t < (self.period_sec * self.duty_cycle)

        if self.occlusion_type == OcclusionType.RANDOM:
            return float(self._rng.uniform(0.0, 1.0)) < self.random_probability

        return False

    def reset(self, seed: Optional[int] = None) -> None:
        """Resets the random number generator."""
        if seed is not None:
            self.seed = seed
        self._rng = np.random.default_rng(self.seed)
