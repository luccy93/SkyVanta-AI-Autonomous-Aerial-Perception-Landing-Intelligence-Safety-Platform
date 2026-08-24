"""Tracking performance and quality metric computation."""

from typing import List
from skyvanta.core.types import Track, TrackLifecycleState, TrackingMetrics


class TrackingMetricsCollector:
    """Aggregates and computes diagnostic metrics across active tracks."""

    @staticmethod
    def compute(tracks: List[Track]) -> TrackingMetrics:
        """Computes summary statistics for the current tracking state."""
        if not tracks:
            return TrackingMetrics()

        active_count = len(tracks)
        confirmed_count = sum(
            1 for t in tracks
            if t.state in (TrackLifecycleState.CONFIRMED, TrackLifecycleState.TRACKING)
        )
        lost_count = sum(
            1 for t in tracks
            if t.state in (TrackLifecycleState.COASTING, TrackLifecycleState.LOST)
        )

        avg_age = sum(t.age for t in tracks) / float(active_count)
        total_missed = sum(t.missed_frames for t in tracks)
        total_age = sum(t.age for t in tracks)
        missed_rate = total_missed / max(1.0, float(total_age))

        return TrackingMetrics(
            active_track_count=active_count,
            confirmed_track_count=confirmed_count,
            lost_track_count=lost_count,
            average_track_age=avg_age,
            missed_frame_rate=missed_rate,
            id_switch_count=0,
        )
