"""Integrated target tracker combining perception, Kalman filtering, and smoothing."""

import math
import random
from collections import deque
from typing import Deque, Optional, Tuple
import numpy as np

from skyvanta.core.types import BoundingBox, TrackState, TrackInfo
from skyvanta.core.config import SkyVantaConfig
from skyvanta.perception.detection.yolo import YoloDroneDetector
from skyvanta.perception.motion.background import MotionContrastDetector
from skyvanta.perception.fusion.candidate_fusion import CandidateFusion
from skyvanta.tracking.kalman import KalmanBox2D
from skyvanta.tracking.smoothing import OneEuroFilter, Vec2EuroFilter
from skyvanta.tracking.state import TrackStateMachine


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class DroneTracker:
    """Tracks target drone / landing pad across consecutive video frames."""

    def __init__(self, frame_shape: Tuple[int, int], config: Optional[SkyVantaConfig] = None):
        self.h, self.w = frame_shape[:2]
        self.config = config or SkyVantaConfig()

        self.yolo = YoloDroneDetector(self.config.perception.detector) if self.config.perception.detector.use_yolo else None
        self.motion = MotionContrastDetector(frame_shape, self.config.perception.motion)
        self.fusion = CandidateFusion(self.config.perception.fusion)

        self.kf = KalmanBox2D(
            process_noise=self.config.tracker.kalman_process_noise,
            measurement_noise=self.config.tracker.kalman_measurement_noise,
        )
        self.center_filter = Vec2EuroFilter(
            min_cutoff=self.config.smoothing.center_min_cutoff,
            beta=self.config.smoothing.center_beta,
        )
        self.size_filter = OneEuroFilter(
            min_cutoff=self.config.smoothing.size_min_cutoff,
            beta=self.config.smoothing.size_beta,
        )
        self.fsm = TrackStateMachine()

        self.track_id = random.randint(1000, 9999)
        self.hits = 0
        self.frames_since_hit = 999
        self.confidence = 0.0
        self.age = 0

        self.last_box: Optional[BoundingBox] = None
        self.last_center: Optional[Tuple[float, float]] = None
        self.last_size: Optional[Tuple[float, float]] = None
        self.trail: Deque[Tuple[float, float]] = deque(maxlen=self.config.tracker.max_trail_length)
        self.scale_history: Deque[float] = deque(maxlen=self.config.tracker.scale_history_length)

    @property
    def state(self) -> TrackState:
        return self.fsm.state

    @property
    def is_visible(self) -> bool:
        return self.last_box is not None and self.frames_since_hit < self.config.tracker.max_lost_frames

    def update(self, frame_bgr: np.ndarray, t_sec: float) -> Tuple[Optional[BoundingBox], float, TrackState]:
        """Processes a single video frame, updates tracking state, and returns current box/confidence/state."""
        self.age += 1
        yolo_detections = self.yolo.detect(frame_bgr) if (self.yolo and self.yolo.is_available) else []
        motion_detections = self.motion.detect(frame_bgr)

        raw_box, det_conf = self.fusion.pick_best(yolo_detections, motion_detections)

        if raw_box is not None:
            cx, cy = raw_box.center
            bw, bh = max(4.0, raw_box.width), max(4.0, raw_box.height)

            if not self.kf.initialized:
                self.kf.init(cx, cy, bw, bh)
            else:
                self.kf.predict()
                self.kf.correct(cx, cy, bw, bh)

            self.frames_since_hit = 0
            self.hits += 1
            self.confidence = lerp(self.confidence, det_conf, 0.25)
        else:
            if self.kf.initialized:
                self.kf.predict()
            self.frames_since_hit += 1
            self.confidence = lerp(self.confidence, 0.0, 0.12)

        if self.kf.initialized:
            kcx, kcy, kw, kh = self.kf.current_state
            kw = max(6.0, float(kw))
            kh = max(6.0, float(kh))
            kcx, kcy = float(kcx), float(kcy)

            s_cx, s_cy = self.center_filter((kcx, kcy), t=t_sec)
            s_size = self.size_filter(math.sqrt(kw * kh), t=t_sec)
            aspect = kw / kh if kh > 0 else 1.0
            s_w = s_size * math.sqrt(aspect)
            s_h = s_size / math.sqrt(aspect)

            s_cx = clamp(s_cx, 0.0, float(self.w))
            s_cy = clamp(s_cy, 0.0, float(self.h))

            jump_ok = True
            if self.trail:
                px, py = self.trail[-1]
                jump_dist = math.hypot(s_cx - px, s_cy - py)
                diag = math.hypot(self.w, self.h)
                if jump_dist > diag * self.config.tracker.jump_distance_ratio:
                    jump_ok = False

            self.last_center = (s_cx, s_cy)
            self.last_size = (s_w, s_h)
            self.last_box = BoundingBox(
                x1=s_cx - s_w / 2.0,
                y1=s_cy - s_h / 2.0,
                x2=s_cx + s_w / 2.0,
                y2=s_cy + s_h / 2.0,
            )
            if not jump_ok:
                self.trail.clear()

            min_step = math.hypot(self.w, self.h) * 0.004
            if not self.trail or math.hypot(s_cx - self.trail[-1][0], s_cy - self.trail[-1][1]) > min_step:
                self.trail.append(self.last_center)
            self.scale_history.append(s_w * s_h)

        self.fsm.update(self.confidence, self.frames_since_hit)
        return self.last_box, self.confidence, self.state

    def scale_trend(self) -> float:
        """Returns relative rate of bounding box area expansion (>0 approaching, <0 receding)."""
        if len(self.scale_history) < 10:
            return 0.0
        hist_list = list(self.scale_history)
        mid = len(hist_list) // 2
        a = float(np.mean(hist_list[:mid]))
        b = float(np.mean(hist_list[mid:]))
        if a <= 1e-3:
            return 0.0
        return clamp((b - a) / a, -1.0, 1.0)

    def get_info(self) -> TrackInfo:
        """Returns a snapshot of the current track information."""
        return TrackInfo(
            track_id=self.track_id,
            state=self.state,
            confidence=self.confidence,
            hits=self.hits,
            frames_since_hit=self.frames_since_hit,
            age=self.age,
            is_visible=self.is_visible,
            bbox=self.last_box,
            center=self.last_center,
            size=self.last_size,
        )
