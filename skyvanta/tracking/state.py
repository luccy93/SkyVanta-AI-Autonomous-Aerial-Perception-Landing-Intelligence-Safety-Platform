"""Tracking state machine logic for visual targets."""

from skyvanta.core.types import TrackState


class TrackStateMachine:
    """Discrete state machine managing target acquisition and tracking transitions."""

    ORDER = [
        TrackState.SEARCHING,
        TrackState.ACQUIRED,
        TrackState.TRACKING,
        TrackState.LOCKED,
        TrackState.APPROACHING,
    ]

    def __init__(self, initial_state: TrackState = TrackState.SEARCHING):
        self.state = initial_state

    def update(self, confidence: float, frames_since_hit: int) -> TrackState:
        """Determines next state based on confidence and missed frame counters."""
        if confidence < 0.12 and frames_since_hit > 15:
            target = TrackState.SEARCHING
        elif confidence < 0.35:
            target = TrackState.ACQUIRED
        elif confidence < 0.60:
            target = TrackState.TRACKING
        elif confidence < 0.80:
            target = TrackState.LOCKED
        else:
            target = TrackState.APPROACHING

        cur_idx = self.ORDER.index(self.state)
        tgt_idx = self.ORDER.index(target)

        if tgt_idx > cur_idx:
            self.state = self.ORDER[min(cur_idx + 1, tgt_idx)]
        elif tgt_idx < cur_idx and frames_since_hit > 20:
            self.state = self.ORDER[max(cur_idx - 1, tgt_idx)]

        return self.state

    def reset(self) -> None:
        """Resets state machine back to SEARCHING."""
        self.state = TrackState.SEARCHING
