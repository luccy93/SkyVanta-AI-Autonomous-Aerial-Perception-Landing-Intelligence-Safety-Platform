"""Deterministic track lifecycle state machine."""

from typing import Optional
from skyvanta.core.config import LifecycleConfig
from skyvanta.core.types import TrackLifecycleState


class TrackLifecycleStateMachine:
    """Manages the life cycle of a single target track:
    TENTATIVE -> CONFIRMED -> TRACKING -> COASTING -> LOST -> DELETED
    """

    def __init__(self, config: Optional[LifecycleConfig] = None):
        self.config = config or LifecycleConfig()
        self.state: TrackLifecycleState = TrackLifecycleState.TENTATIVE
        self.hits: int = 1
        self.consecutive_hits: int = 1
        self.missed_frames: int = 0
        self.age: int = 1

    def step(self, has_measurement: bool) -> TrackLifecycleState:
        """Updates lifecycle state based on detection measurement presence.

        Returns:
            The new TrackLifecycleState.
        """
        self.age += 1

        if has_measurement:
            self.hits += 1
            self.consecutive_hits += 1
            self.missed_frames = 0

            if self.state == TrackLifecycleState.TENTATIVE:
                if self.hits >= self.config.min_confirmed_hits:
                    self.state = TrackLifecycleState.CONFIRMED
            elif self.state in (TrackLifecycleState.CONFIRMED, TrackLifecycleState.COASTING, TrackLifecycleState.LOST):
                self.state = TrackLifecycleState.TRACKING

        else:
            self.consecutive_hits = 0
            self.missed_frames += 1

            if self.state == TrackLifecycleState.TENTATIVE:
                if self.missed_frames >= self.config.max_tentative_misses:
                    self.state = TrackLifecycleState.DELETED
            elif self.state in (TrackLifecycleState.CONFIRMED, TrackLifecycleState.TRACKING):
                self.state = TrackLifecycleState.COASTING
            elif self.state == TrackLifecycleState.COASTING:
                if self.missed_frames >= self.config.max_coasting_frames:
                    self.state = TrackLifecycleState.LOST
            elif self.state == TrackLifecycleState.LOST:
                if self.missed_frames >= self.config.max_lost_frames:
                    self.state = TrackLifecycleState.DELETED

        return self.state

    def force_delete(self) -> None:
        """Immediately marks track as DELETED."""
        self.state = TrackLifecycleState.DELETED
