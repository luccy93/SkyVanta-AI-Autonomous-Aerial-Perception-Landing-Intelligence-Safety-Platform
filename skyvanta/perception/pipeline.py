"""Unified Perception Pipeline orchestrating detection, motion, optical flow, and fusion."""

import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from skyvanta.core.config import PerceptionConfig, SkyVantaConfig
from skyvanta.core.logging import get_logger
from skyvanta.core.types import (
    BoundingBox,
    Candidate,
    Detection,
    MotionCandidate,
    OpticalFlowResult,
    PerceptionFrameResult,
    PerceptionTiming,
)
from skyvanta.perception.detection.base import BaseDetector
from skyvanta.perception.detection.yolo import YoloDroneDetector
from skyvanta.perception.fusion.candidate_fusion import CandidateFusionEngine
from skyvanta.perception.motion.background import BackgroundSubtractorMotionDetector
from skyvanta.perception.motion.base import BaseMotionDetector
from skyvanta.perception.motion.optical_flow import FarnebackOpticalFlow
from skyvanta.perception.selection.target_selector import TargetSelector
from skyvanta.perception.validation import FrameValidator

logger = get_logger("skyvanta.perception.pipeline")


class PerceptionPipeline:
    """Production Computer Vision Perception Pipeline.

    Orchestrates:
        1. Frame Validation & Sanitization
        2. Deep Learning Object Detection (YOLO / Mock)
        3. Background Subtraction & Contour Motion Analysis
        4. Dense Farneback Optical Flow & Vector Field Analysis
        5. Multi-cue Candidate Fusion & Scoring
        6. Target Selection & Provenance Tracking
    """

    def __init__(
        self,
        frame_shape: Tuple[int, int],
        config: Optional[PerceptionConfig] = None,
        detector: Optional[BaseDetector] = None,
        motion_detector: Optional[BaseMotionDetector] = None,
        optical_flow: Optional[FarnebackOpticalFlow] = None,
    ):
        self.frame_shape = frame_shape
        self.config = config or PerceptionConfig()

        # Instantiate or inject modular components
        self.validator = FrameValidator()
        self.detector = detector or YoloDroneDetector(self.config.detector)
        self.motion_detector = motion_detector or BackgroundSubtractorMotionDetector(
            frame_shape, self.config.motion
        )
        self.optical_flow = optical_flow or FarnebackOpticalFlow(self.config.optical_flow)
        self.fusion_engine = CandidateFusionEngine(self.config.fusion)
        self.target_selector = TargetSelector(self.config.selection)

        self._frame_count = 0
        logger.info(
            "PerceptionPipeline initialized for frame size %dx%d (YOLO: %s, Motion: %s, Flow: %s)",
            frame_shape[1], frame_shape[0],
            self.detector.is_available,
            self.config.motion.enabled,
            self.config.optical_flow.enabled,
        )

    def reset(self) -> None:
        """Resets internal state for all temporal filters and detectors."""
        self.motion_detector.reset()
        self.optical_flow.reset()
        self._frame_count = 0

    def process(
        self,
        frame_bgr: np.ndarray,
        frame_id: Optional[int] = None,
        timestamp_sec: Optional[float] = None,
    ) -> PerceptionFrameResult:
        """Executes the full perception workflow on a single video frame with latency instrumentation."""
        t_total_start = time.perf_counter()
        fid = frame_id if frame_id is not None else self._frame_count
        t_sec = timestamp_sec if timestamp_sec is not None else (fid / 30.0)
        self._frame_count += 1

        timing = PerceptionTiming()

        # Step 1: Frame Validation
        t_val_start = time.perf_counter()
        is_valid, err_msg = self.validator.validate(frame_bgr)
        timing.validation_ms = (time.perf_counter() - t_val_start) * 1000.0

        if not is_valid:
            timing.total_ms = (time.perf_counter() - t_total_start) * 1000.0
            logger.warning("Frame %d failed validation: %s", fid, err_msg)
            return PerceptionFrameResult(
                frame_id=fid,
                timestamp_sec=t_sec,
                is_valid_frame=False,
                timing=timing,
                diagnostics={"validation_error": err_msg},
            )

        # Step 2: Semantic Object Detection
        t_det_start = time.perf_counter()
        detections: List[Detection] = []
        if self.detector.is_available:
            detections = self.detector.detect(
                frame_bgr,
                frame_id=fid,
                timestamp_sec=t_sec,
            )
        timing.detection_ms = (time.perf_counter() - t_det_start) * 1000.0

        # Step 3: Motion Detection
        t_mot_start = time.perf_counter()
        motion_candidates: List[MotionCandidate] = []
        if self.config.motion.enabled:
            motion_candidates = self.motion_detector.detect(frame_bgr)
        timing.motion_ms = (time.perf_counter() - t_mot_start) * 1000.0

        # Step 4: Optical Flow Analysis
        t_flow_start = time.perf_counter()
        flow_result = None
        if self.config.optical_flow.enabled:
            flow_result = self.optical_flow.compute(frame_bgr)
        timing.optical_flow_ms = (time.perf_counter() - t_flow_start) * 1000.0

        # Flow energy closure for candidate fusion
        def roi_flow_energy(bbox: BoundingBox) -> float:
            if not self.config.optical_flow.enabled:
                return 0.0
            return self.optical_flow.extract_roi_flow_energy(bbox, frame_bgr.shape[:2])

        # Step 5: Candidate Fusion & Scoring
        t_fus_start = time.perf_counter()
        fused_candidates = self.fusion_engine.fuse(
            detections=detections,
            motion_candidates=motion_candidates,
            flow_energy_fn=roi_flow_energy,
        )
        timing.fusion_ms = (time.perf_counter() - t_fus_start) * 1000.0

        # Step 6: Target Selection
        t_sel_start = time.perf_counter()
        selected_target = self.target_selector.select(
            candidates=fused_candidates,
            frame_shape=frame_bgr.shape[:2],
        )
        timing.selection_ms = (time.perf_counter() - t_sel_start) * 1000.0

        timing.total_ms = (time.perf_counter() - t_total_start) * 1000.0

        return PerceptionFrameResult(
            frame_id=fid,
            timestamp_sec=t_sec,
            is_valid_frame=True,
            detections=detections,
            motion_candidates=motion_candidates,
            optical_flow=flow_result,
            fused_candidates=fused_candidates,
            selected_target=selected_target,
            timing=timing,
            diagnostics={
                "detector_available": self.detector.is_available,
                "detection_count": len(detections),
                "motion_count": len(motion_candidates),
                "fused_count": len(fused_candidates),
            },
        )
