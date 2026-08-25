"""Latency and transmission delay simulation models."""

from collections import deque
from typing import Any, Deque, List, Optional, Tuple
import numpy as np
from pydantic import BaseModel, Field


class LatencyType(str):
    FIXED = "FIXED"
    GAUSSIAN = "GAUSSIAN"
    BOUNDED_UNIFORM = "BOUNDED_UNIFORM"


class LatencyModel:
    """Simulates communication, sensor capture, and processing delays with FIFO queueing."""

    def __init__(
        self,
        mean_latency_sec: float = 0.0,
        jitter_sigma_sec: float = 0.0,
        min_latency_sec: float = 0.0,
        max_latency_sec: float = 1.0,
        timestamp_offset_sec: float = 0.0,
        seed: Optional[int] = None,
    ):
        self.mean_latency_sec = max(0.0, float(mean_latency_sec))
        self.jitter_sigma_sec = max(0.0, float(jitter_sigma_sec))
        self.min_latency_sec = max(0.0, float(min_latency_sec))
        self.max_latency_sec = max(self.min_latency_sec, float(max_latency_sec))
        self.timestamp_offset_sec = float(timestamp_offset_sec)
        self.seed = seed
        self._rng = np.random.default_rng(seed)
        self._queue: Deque[Tuple[float, Any]] = deque()  # (delivery_time, payload)

    def sample_delay(self) -> float:
        """Computes a stochastic delivery delay based on configured parameters."""
        if self.jitter_sigma_sec <= 0.0:
            delay = self.mean_latency_sec
        else:
            raw = self._rng.normal(self.mean_latency_sec, self.jitter_sigma_sec)
            delay = float(np.clip(raw, self.min_latency_sec, self.max_latency_sec))
        return delay

    def push(self, item: Any, current_time_sec: float) -> float:
        """Pushes an item into the latency pipeline.

        Args:
            item: Sensor observation, command, or telemetry packet.
            current_time_sec: Current simulation timestamp.

        Returns:
            Calculated scheduled delivery timestamp.
        """
        delay = self.sample_delay()
        delivery_time = current_time_sec + delay + self.timestamp_offset_sec
        self._queue.append((delivery_time, item))
        return delivery_time

    def pop_ready(self, current_time_sec: float) -> List[Any]:
        """Extracts all items whose delivery time has arrived by current_time_sec.

        Args:
            current_time_sec: Current simulation timestamp.

        Returns:
            List of delivered items in arrival order.
        """
        ready_items: List[Any] = []
        while self._queue and self._queue[0][0] <= current_time_sec:
            _, item = self._queue.popleft()
            ready_items.append(item)
        return ready_items

    def peek_next_delivery_time(self) -> Optional[float]:
        """Returns the scheduled delivery time of the earliest pending item, or None."""
        return self._queue[0][0] if self._queue else None

    @property
    def pending_count(self) -> int:
        """Returns the number of buffered items in flight."""
        return len(self._queue)

    def clear(self) -> None:
        """Clears all pending buffered items."""
        self._queue.clear()

    def reset(self, seed: Optional[int] = None) -> None:
        """Resets the queue and random number generator."""
        self.clear()
        if seed is not None:
            self.seed = seed
        self._rng = np.random.default_rng(self.seed)


class SubsystemLatencyConfig(BaseModel):
    """Latency configuration parameters partitioned across all major subsystems."""
    camera_latency_sec: float = Field(default=0.03, ge=0.0, description="Camera exposure and ISP pipeline latency (seconds)")
    imu_latency_sec: float = Field(default=0.002, ge=0.0, description="IMU sampling and SPI bus latency (seconds)")
    pose_latency_sec: float = Field(default=0.02, ge=0.0, description="Visual PnP pose estimation compute latency (seconds)")
    telemetry_latency_sec: float = Field(default=0.01, ge=0.0, description="Autopilot telemetry transmission latency (seconds)")
    autopilot_command_latency_sec: float = Field(default=0.02, ge=0.0, description="Command dispatch and actuator lag (seconds)")
    random_seed: Optional[int] = Field(default=42, description="RNG seed for latency jitter")
