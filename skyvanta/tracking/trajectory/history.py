"""Bounded historical trajectory management and image velocity estimation."""

from collections import deque
from typing import Deque, List, Optional, Tuple
import numpy as np

from skyvanta.core.config import TrajectoryConfig
from skyvanta.core.types import BoundingBox, TrackLifecycleState, TrajectoryPoint


class TrajectoryHistory:
    """Maintains a bounded historical window of track positions and estimates image-space velocity."""

    def __init__(self, config: Optional[TrajectoryConfig] = None):
        self.config = config or TrajectoryConfig()
        self.points: Deque[TrajectoryPoint] = deque(maxlen=self.config.max_history_length)
        self.smoothed_velocity: Tuple[float, float] = (0.0, 0.0)

    def append(
        self,
        bbox: BoundingBox,
        timestamp_sec: float,
        confidence: float = 1.0,
        state: TrackLifecycleState = TrackLifecycleState.TRACKING,
    ) -> None:
        """Appends a new trajectory point and updates velocity estimation."""
        cx, cy = bbox.center
        pt = TrajectoryPoint(
            x=cx,
            y=cy,
            w=bbox.width,
            h=bbox.height,
            timestamp_sec=timestamp_sec,
            confidence=confidence,
            state=state,
        )

        if self.points:
            prev = self.points[-1]
            dt = max(1e-3, timestamp_sec - prev.timestamp_sec)
            inst_vx = (cx - prev.x) / dt
            inst_vy = (cy - prev.y) / dt

            # EMA velocity smoothing
            alpha = self.config.velocity_smoothing_alpha
            svx = alpha * inst_vx + (1.0 - alpha) * self.smoothed_velocity[0]
            svy = alpha * inst_vy + (1.0 - alpha) * self.smoothed_velocity[1]
            self.smoothed_velocity = (float(svx), float(svy))

        self.points.append(pt)

    def get_points(self) -> List[TrajectoryPoint]:
        """Returns ordered trajectory points from oldest to newest."""
        return list(self.points)

    @property
    def current_velocity_px_per_sec(self) -> Tuple[float, float]:
        """Returns the current smoothed image-space velocity in pixels/second."""
        return self.smoothed_velocity

    def scale_expansion_rate(self) -> float:
        """Computes relative area rate of expansion (>0 approaching, <0 receding)."""
        if len(self.points) < 8:
            return 0.0
        areas = [p.w * p.h for p in self.points if p.w and p.h]
        if len(areas) < 8:
            return 0.0

        mid = len(areas) // 2
        a = float(np.mean(areas[:mid]))
        b = float(np.mean(areas[mid:]))
        if a <= 1.0:
            return 0.0
        return max(-1.0, min(1.0, (b - a) / a))

    def clear(self) -> None:
        """Clears all historical trajectory points."""
        self.points.clear()
        self.smoothed_velocity = (0.0, 0.0)
