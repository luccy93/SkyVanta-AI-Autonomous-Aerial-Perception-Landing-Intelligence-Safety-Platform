"""Multi-target track manager coordinating Kalman filtering, association, lifecycle, and trajectory."""

import math
import time
from typing import Any, Dict, List, Optional, Tuple

from skyvanta.core.config import SmoothingConfig, TrackingConfig
from skyvanta.core.logging import get_logger
from skyvanta.core.types import (
    BoundingBox,
    Candidate,
    Detection,
    DetectionSource,
    PerceptionFrameResult,
    Track,
    TrackLifecycleState,
    TrackingMetrics,
    TrackingResult,
    TrackingTiming,
)
from skyvanta.tracking.association.iou import IoUAssociator
from skyvanta.tracking.filters.kalman import KalmanBox2D
from skyvanta.tracking.filters.smoothing import OneEuroFilter, Vec2EuroFilter
from skyvanta.tracking.lifecycle.state_machine import TrackLifecycleStateMachine
from skyvanta.tracking.metrics.tracking_metrics import TrackingMetricsCollector
from skyvanta.tracking.trajectory.history import TrajectoryHistory

logger = get_logger("skyvanta.tracking.manager")


class _InternalTrackState:
    """Internal runtime wrapper holding stateful filters for a single track."""

    def __init__(
        self,
        track_id: int,
        initial_box: BoundingBox,
        confidence: float,
        timestamp_sec: float,
        source_class: str = "drone",
        source: DetectionSource = DetectionSource.YOLO,
        tracking_config: Optional[TrackingConfig] = None,
        smoothing_config: Optional[SmoothingConfig] = None,
    ):
        t_cfg = tracking_config or TrackingConfig()
        s_cfg = smoothing_config or SmoothingConfig()

        self.track_id = track_id
        self.source_class = source_class
        self.source = source
        self.created_at_sec = timestamp_sec
        self.last_seen_sec = timestamp_sec

        self.kf = KalmanBox2D(
            process_noise=t_cfg.kalman_process_noise,
            measurement_noise=t_cfg.kalman_measurement_noise,
        )
        cx, cy = initial_box.center
        self.kf.init(cx, cy, initial_box.width, initial_box.height)

        self.center_filter = Vec2EuroFilter(
            min_cutoff=s_cfg.center_min_cutoff,
            beta=s_cfg.center_beta,
        )
        self.size_filter = OneEuroFilter(
            min_cutoff=s_cfg.size_min_cutoff,
            beta=s_cfg.size_beta,
        )

        self.lifecycle = TrackLifecycleStateMachine(t_cfg.lifecycle)
        self.trajectory = TrajectoryHistory(t_cfg.trajectory)

        self.confidence = float(confidence)
        self.predicted_box: Optional[BoundingBox] = None
        self.current_box: BoundingBox = initial_box

        # Log initial trajectory point
        self.trajectory.append(
            initial_box,
            timestamp_sec=timestamp_sec,
            confidence=self.confidence,
            state=self.lifecycle.state,
        )

    def predict(self) -> BoundingBox:
        """Runs Kalman prediction and updates predicted_box."""
        pcx, pcy, pw, ph = self.kf.predict()
        self.predicted_box = BoundingBox(
            x1=pcx - pw / 2.0,
            y1=pcy - ph / 2.0,
            x2=pcx + pw / 2.0,
            y2=pcy + ph / 2.0,
        )
        return self.predicted_box

    def update_matched(
        self,
        measurement_box: BoundingBox,
        detection_confidence: float,
        timestamp_sec: float,
    ) -> None:
        """Updates track state with an associated measurement."""
        mcx, mcy = measurement_box.center
        mw, mh = measurement_box.width, measurement_box.height

        # Kalman correction
        kcx, kcy, kw, kh = self.kf.correct(mcx, mcy, mw, mh)

        # Adaptive smoothing
        scx, scy = self.center_filter((kcx, kcy), t=timestamp_sec)
        ssize = self.size_filter(math.sqrt(kw * kh), t=timestamp_sec)
        aspect = kw / kh if kh > 0 else 1.0
        sw = max(4.0, ssize * math.sqrt(aspect))
        sh = max(4.0, ssize / math.sqrt(aspect))

        self.current_box = BoundingBox(
            x1=scx - sw / 2.0,
            y1=scy - sh / 2.0,
            x2=scx + sw / 2.0,
            y2=scy + sh / 2.0,
        )

        self.confidence = 0.75 * self.confidence + 0.25 * float(detection_confidence)
        self.last_seen_sec = timestamp_sec
        self.lifecycle.step(has_measurement=True)

        self.trajectory.append(
            self.current_box,
            timestamp_sec=timestamp_sec,
            confidence=self.confidence,
            state=self.lifecycle.state,
        )

    def update_unmatched(self, timestamp_sec: float) -> None:
        """Updates track state when no measurement was associated."""
        if self.predicted_box is not None:
            pcx, pcy = self.predicted_box.center
            pw, ph = self.predicted_box.width, self.predicted_box.height

            scx, scy = self.center_filter((pcx, pcy), t=timestamp_sec)
            self.current_box = BoundingBox(
                x1=scx - pw / 2.0,
                y1=scy - ph / 2.0,
                x2=scx + pw / 2.0,
                y2=scy + ph / 2.0,
            )

        self.confidence = max(0.0, self.confidence * 0.88)
        self.lifecycle.step(has_measurement=False)

        self.trajectory.append(
            self.current_box,
            timestamp_sec=timestamp_sec,
            confidence=self.confidence,
            state=self.lifecycle.state,
        )

    def compute_quality(self, config: TrackingConfig) -> float:
        """Calculates composite track quality score [0.0, 1.0]."""
        hit_ratio = self.lifecycle.hits / max(1.0, float(self.lifecycle.age))
        conf_factor = self.confidence
        continuity = min(1.0, self.lifecycle.consecutive_hits / 5.0)

        w_h = config.quality.weight_hit_ratio
        w_c = config.quality.weight_confidence
        w_cont = config.quality.weight_continuity

        q = w_h * hit_ratio + w_c * conf_factor + w_cont * continuity
        return max(0.0, min(1.0, float(q)))

    def to_public_track(self, config: TrackingConfig) -> Track:
        """Exports public strongly typed Track representation."""
        return Track(
            track_id=self.track_id,
            state=self.lifecycle.state,
            bbox=self.current_box,
            predicted_bbox=self.predicted_box,
            confidence=float(self.confidence),
            track_quality=self.compute_quality(config),
            age=self.lifecycle.age,
            hits=self.lifecycle.hits,
            consecutive_hits=self.lifecycle.consecutive_hits,
            missed_frames=self.lifecycle.missed_frames,
            velocity_px_per_sec=self.trajectory.current_velocity_px_per_sec,
            source_class=self.source_class,
            source=self.source,
            trajectory=self.trajectory.get_points(),
            created_at_sec=self.created_at_sec,
            last_seen_sec=self.last_seen_sec,
        )


class MultiTargetTrackManager:
    """Production Multi-Target Tracker managing prediction, data association, Kalman updates, and lifecycle."""

    def __init__(
        self,
        config: Optional[TrackingConfig] = None,
        smoothing_config: Optional[SmoothingConfig] = None,
    ):
        self.config = config or TrackingConfig()
        self.smoothing_config = smoothing_config or SmoothingConfig()
        self.associator = IoUAssociator(self.config.association)

        self._tracks: Dict[int, _InternalTrackState] = {}
        self._next_track_id: int = 1
        self._frame_count: int = 0

    def reset(self) -> None:
        """Clears all active tracks and resets internal state."""
        self._tracks.clear()
        self._next_track_id = 1
        self._frame_count = 0

    def process(
        self,
        perception_result: PerceptionFrameResult,
        timestamp_sec: Optional[float] = None,
    ) -> TrackingResult:
        """Processes a single frame's perception outputs and updates all tracks."""
        t_total_start = time.perf_counter()
        fid = perception_result.frame_id
        t_sec = timestamp_sec if timestamp_sec is not None else perception_result.timestamp_sec
        self._frame_count += 1

        timing = TrackingTiming()

        # Step 1: Predict state for all active tracks
        t_pred_start = time.perf_counter()
        track_list = list(self._tracks.values())
        for trk in track_list:
            trk.predict()
        timing.prediction_ms = (time.perf_counter() - t_pred_start) * 1000.0

        # Step 2: Extract candidate detections from perception
        candidate_boxes: List[BoundingBox] = []
        candidate_confs: List[float] = []
        candidate_classes: List[str] = []
        candidate_sources: List[DetectionSource] = []

        if perception_result.fused_candidates:
            for cand in perception_result.fused_candidates:
                candidate_boxes.append(cand.bbox)
                candidate_confs.append(cand.candidate_score)
                candidate_classes.append(cand.class_name)
                candidate_sources.append(cand.source)
        elif perception_result.detections:
            for det in perception_result.detections:
                candidate_boxes.append(det.bbox)
                candidate_confs.append(det.confidence)
                candidate_classes.append(det.class_name)
                candidate_sources.append(det.source)

        # Step 3: Data Association
        t_assoc_start = time.perf_counter()
        public_tracks_for_assoc = [trk.to_public_track(self.config) for trk in track_list]
        matches, unmatched_track_indices, unmatched_det_indices = self.associator.associate(
            tracks=public_tracks_for_assoc,
            detections=candidate_boxes,
        )
        timing.association_ms = (time.perf_counter() - t_assoc_start) * 1000.0

        # Step 4: Measurement Update
        t_upd_start = time.perf_counter()
        for t_idx, d_idx in matches:
            trk = track_list[t_idx]
            trk.update_matched(
                measurement_box=candidate_boxes[d_idx],
                detection_confidence=candidate_confs[d_idx],
                timestamp_sec=t_sec,
            )

        for t_idx in unmatched_track_indices:
            trk = track_list[t_idx]
            trk.update_unmatched(timestamp_sec=t_sec)

        # Step 5: Initiate New Tracks for Unmatched Detections
        for d_idx in unmatched_det_indices:
            conf = candidate_confs[d_idx]
            if conf >= 0.20:
                tid = self._next_track_id
                self._next_track_id += 1
                new_track = _InternalTrackState(
                    track_id=tid,
                    initial_box=candidate_boxes[d_idx],
                    confidence=conf,
                    timestamp_sec=t_sec,
                    source_class=candidate_classes[d_idx],
                    source=candidate_sources[d_idx],
                    tracking_config=self.config,
                    smoothing_config=self.smoothing_config,
                )
                self._tracks[tid] = new_track
        timing.update_ms = (time.perf_counter() - t_upd_start) * 1000.0

        # Step 6: Lifecycle Management and Deletion Purge
        t_life_start = time.perf_counter()
        deleted_ids: List[int] = []
        for tid, trk in list(self._tracks.items()):
            if trk.lifecycle.state == TrackLifecycleState.DELETED:
                deleted_ids.append(tid)
                del self._tracks[tid]
        timing.lifecycle_ms = (time.perf_counter() - t_life_start) * 1000.0

        # Step 7: Assemble Result Objects
        all_tracks = [t.to_public_track(self.config) for t in self._tracks.values()]
        confirmed_tracks = [
            t for t in all_tracks
            if t.state in (TrackLifecycleState.CONFIRMED, TrackLifecycleState.TRACKING)
        ]
        lost_tracks = [
            t for t in all_tracks
            if t.state in (TrackLifecycleState.COASTING, TrackLifecycleState.LOST)
        ]

        metrics = TrackingMetricsCollector.compute(all_tracks)
        timing.total_ms = (time.perf_counter() - t_total_start) * 1000.0

        return TrackingResult(
            frame_id=fid,
            timestamp_sec=t_sec,
            tracks=all_tracks,
            confirmed_tracks=confirmed_tracks,
            lost_tracks=lost_tracks,
            deleted_track_ids=deleted_ids,
            timing=timing,
            metrics=metrics,
        )

    def get_track(self, track_id: int) -> Optional[Track]:
        """Retrieves a single active track by ID."""
        if track_id in self._tracks:
            return self._tracks[track_id].to_public_track(self.config)
        return None
