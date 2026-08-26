"""Pipeline orchestrator for video ingestion, perception, tracking, estimation, and rendering."""

import os
import time
from typing import Optional
import cv2
import numpy as np

from skyvanta.core.config import SkyVantaConfig
from skyvanta.core.exceptions import VideoSourceError
from skyvanta.core.logging import get_logger
from skyvanta.core.types import BoundingBox, FrameMetadata, PerceptionResult
from skyvanta.simulation.synthetic import SyntheticSceneGenerator
from skyvanta.telemetry.estimator import TelemetryEstimator
from skyvanta.tracking.tracker import DroneTracker
from skyvanta.visualization.corridor import ApproachCorridor
from skyvanta.visualization.hud import HUDRenderer

logger = get_logger("skyvanta.pipeline.runner")


def open_video_writer(path: str, fps: float, size: tuple) -> cv2.VideoWriter:
    """Attempts opening VideoWriter using multiple common FourCC codecs."""
    fourcc_options = ["mp4v", "avc1", "H264"]
    for fcc in fourcc_options:
        fourcc = cv2.VideoWriter_fourcc(*fcc)
        vw = cv2.VideoWriter(path, fourcc, fps, size)
        if vw.isOpened():
            return vw
        vw.release()
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    fallback_path = path.replace(".mp4", ".avi")
    return cv2.VideoWriter(fallback_path, fourcc, fps, size)


class PipelineRunner:
    """Executes the SkyVanta perception pipeline on input videos or procedural synthetic scenes."""

    def __init__(self, config: Optional[SkyVantaConfig] = None):
        self.config = config or SkyVantaConfig()
        os.makedirs(self.config.pipeline.output_dir, exist_ok=True)

    def process_frame(
        self,
        frame_bgr: np.ndarray,
        tracker: DroneTracker,
        telemetry_est: TelemetryEstimator,
        corridor_engine: ApproachCorridor,
        t_sec: float,
        frame_idx: int = 0,
        fps: float = 30.0,
    ) -> PerceptionResult:
        """Processes a single video frame through perception, tracking, and telemetry estimators."""
        h, w = frame_bgr.shape[:2]
        tracker.update(frame_bgr, t_sec)

        telemetry = None
        if tracker.is_visible:
            telemetry = telemetry_est.estimate(
                tracker.last_center,
                tracker.last_size,
                tracker.confidence,
                tracker.scale_trend(),
                t_sec,
            )

        corridor = corridor_engine.update(tracker.last_center, tracker.last_size, t_sec)
        track_info = tracker.get_info()

        metadata = FrameMetadata(
            frame_index=frame_idx,
            timestamp_sec=t_sec,
            source_width=w,
            source_height=h,
            processed_width=w,
            processed_height=h,
            fps=fps,
        )

        return PerceptionResult(
            metadata=metadata,
            track=track_info,
            telemetry=telemetry,
            corridor=corridor,
        )

    def process_video(self, input_path: str, output_path: Optional[str] = None) -> str:
        """Runs the pipeline over a video file on disk."""
        if not os.path.isfile(input_path):
            raise VideoSourceError(f"Input video file not found: {input_path}")

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise VideoSourceError(f"Could not open video file: {input_path}")

        src_fps = cap.get(cv2.CAP_PROP_FPS)
        if not src_fps or src_fps <= 1.0 or src_fps > 120.0:
            src_fps = self.config.pipeline.default_fps

        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if src_w <= 0 or src_h <= 0:
            cap.release()
            raise VideoSourceError(f"Invalid video dimensions: {src_w}x{src_h}")

        proc_w, proc_h = src_w, src_h
        max_dim = self.config.pipeline.max_dimension
        scale = 1.0
        if max(src_w, src_h) > max_dim:
            scale = max_dim / max(src_w, src_h)
            proc_w, proc_h = int(src_w * scale), int(src_h * scale)
            proc_w -= proc_w % 2
            proc_h -= proc_h % 2

        if output_path is None:
            base = os.path.splitext(os.path.basename(input_path))[0]
            output_path = os.path.join(self.config.pipeline.output_dir, f"{base}_perception.mp4")

        writer = open_video_writer(output_path, src_fps, (proc_w, proc_h))
        if not writer.isOpened():
            cap.release()
            raise VideoSourceError(f"Could not open video writer for {output_path}")

        tracker = DroneTracker((proc_h, proc_w), self.config)
        telemetry_est = TelemetryEstimator((proc_h, proc_w), self.config)
        corridor_engine = ApproachCorridor((proc_h, proc_w), self.config)
        hud = HUDRenderer((proc_h, proc_w), self.config)

        logger.info("Processing '%s' (%dx%d @ %.1ffps) -> output '%s'", input_path, src_w, src_h, src_fps, output_path)

        frame_idx = 0
        t_start = time.time()
        last_log = t_start

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if scale != 1.0:
                    frame = cv2.resize(frame, (proc_w, proc_h), interpolation=cv2.INTER_AREA)

                t_sec = frame_idx / src_fps
                result = self.process_frame(frame, tracker, telemetry_est, corridor_engine, t_sec, frame_idx, src_fps)

                rendered = hud.render(
                    frame,
                    result.track,
                    result.telemetry,
                    result.corridor,
                    t_sec,
                    real_fps=src_fps,
                )
                writer.write(rendered)
                frame_idx += 1

                if time.time() - last_log > 2.0:
                    pct = (frame_idx / total_frames * 100.0) if total_frames > 0 else 0.0
                    state_str = result.track.state.value if result.track else "SEARCHING"
                    conf_val = result.track.confidence if result.track else 0.0
                    logger.info("Frame %d/%s (%.1f%%) state=%s conf=%.2f", frame_idx, total_frames if total_frames > 0 else "?", pct, state_str, conf_val)
                    last_log = time.time()
        finally:
            cap.release()
            writer.release()

        logger.info("Completed processing %d frames -> %s", frame_idx, output_path)
        return output_path

    def run_demo(self, output_path: Optional[str] = None) -> str:
        """Executes full perception pipeline over procedurally generated aerial synthetic scene."""
        target_w, target_h = 1280, 720
        fps = self.config.pipeline.default_fps
        duration_sec = self.config.pipeline.demo_duration_sec

        generator = SyntheticSceneGenerator(
            width=target_w,
            height=target_h,
            fps=fps,
            duration_sec=duration_sec,
        )

        if output_path is None:
            output_path = os.path.join(self.config.pipeline.output_dir, "demo_perception.mp4")

        writer = open_video_writer(output_path, fps, (target_w, target_h))
        if not writer.isOpened():
            raise VideoSourceError(f"Could not open video writer for {output_path}")

        # Disable YOLO in demo generator to run fast procedural simulation
        demo_config = self.config.model_copy(deep=True)
        demo_config.perception.detector.use_yolo = False

        tracker = DroneTracker((target_h, target_w), demo_config)
        telemetry_est = TelemetryEstimator((target_h, target_w), demo_config)
        corridor_engine = ApproachCorridor((target_h, target_w), demo_config)
        hud = HUDRenderer((target_h, target_w), demo_config)

        logger.info("Rendering %d synthetic frames (%.0fs @ %.0ffps) -> %s", generator.n_frames, duration_sec, fps, output_path)

        for i, t_sec, frame, (cx, cy, sw, sh), present in generator.generate_frames():
            # Inject synthetic target into tracking filter
            if present:
                if not tracker.kf.initialized:
                    tracker.kf.init(cx, cy, sw, sh)
                else:
                    tracker.kf.predict()
                    tracker.kf.correct(cx, cy, sw, sh)
                tracker.frames_since_hit = 0
                tracker.hits += 1
                tracker.confidence = tracker.confidence + (0.90 - tracker.confidence) * 0.20
            else:
                if tracker.kf.initialized:
                    tracker.kf.predict()
                tracker.frames_since_hit += 1
                tracker.confidence = tracker.confidence + (0.05 - tracker.confidence) * 0.15

            if tracker.kf.initialized:
                kcx, kcy, kw, kh = tracker.kf.current_state
                kw = max(6.0, float(kw))
                kh = max(6.0, float(kh))
                s_cx, s_cy = tracker.center_filter((float(kcx), float(kcy)), t=t_sec)
                s_size = tracker.size_filter(np.sqrt(kw * kh), t=t_sec)
                aspect = kw / kh if kh > 0 else 1.0
                s_w = s_size * np.sqrt(aspect)
                s_h = s_size / np.sqrt(aspect)

                tracker.last_center = (s_cx, s_cy)
                tracker.last_size = (s_w, s_h)
                tracker.last_box = BoundingBox(
                    x1=s_cx - s_w / 2.0,
                    y1=s_cy - s_h / 2.0,
                    x2=s_cx + s_w / 2.0,
                    y2=s_cy + s_h / 2.0,
                )
                min_step = np.hypot(tracker.w, tracker.h) * 0.004
                if not tracker.trail or np.hypot(s_cx - tracker.trail[-1][0], s_cy - tracker.trail[-1][1]) > min_step:
                    tracker.trail.append(tracker.last_center)
                tracker.scale_history.append(s_w * s_h)

            tracker.age += 1
            tracker.fsm.update(tracker.confidence, tracker.frames_since_hit)

            telemetry = None
            if tracker.is_visible:
                telemetry = telemetry_est.estimate(
                    tracker.last_center,
                    tracker.last_size,
                    tracker.confidence,
                    tracker.scale_trend(),
                    t_sec,
                )
            corridor = corridor_engine.update(tracker.last_center, tracker.last_size, t_sec)
            track_info = tracker.get_info()

            rendered = hud.render(frame, track_info, telemetry, corridor, t_sec, real_fps=fps)
            writer.write(rendered)

            if i % int(fps * 2) == 0:
                logger.info("Demo progress: frame %d/%d state=%s", i, generator.n_frames, tracker.state.value)

        writer.release()
        logger.info("Demo rendering complete -> %s", output_path)
        return output_path
