"""Tests for skyvanta.perception public exports and modular subpackage integrity."""

import inspect
import skyvanta.perception as perception
from skyvanta.perception.detection.base import BaseDetector
from skyvanta.perception.motion.base import BaseMotionDetector
from skyvanta.perception.detection.yolo import YoloDroneDetector
from skyvanta.perception.fusion.candidate_fusion import CandidateFusion, CandidateFusionEngine
from skyvanta.perception.fusion.scoring import CandidateScorer
from skyvanta.perception.motion.background import (
    BackgroundSubtractorMotionDetector,
    MotionContrastDetector,
)
from skyvanta.perception.motion.optical_flow import FarnebackOpticalFlow
from skyvanta.perception.selection.target_selector import TargetSelector
from skyvanta.perception.pipeline import PerceptionPipeline


def test_top_level_perception_exports():
    """Verify that skyvanta.perception exports all expected public APIs."""
    expected_exports = [
        "BaseDetector",
        "BaseMotionDetector",
        "BoundingBox",
        "Detection",
        "DetectionSource",
        "MotionCandidate",
        "OpticalFlowResult",
        "Candidate",
        "PerceptionTiming",
        "PerceptionFrameResult",
        "FrameValidator",
        "YoloDroneDetector",
        "MockDetector",
        "DetectionParser",
        "BackgroundSubtractorMotionDetector",
        "MotionContrastDetector",
        "FarnebackOpticalFlow",
        "CandidateFusionEngine",
        "CandidateFusion",
        "CandidateScorer",
        "TargetSelector",
        "PerceptionPipeline",
    ]
    for sym in expected_exports:
        assert hasattr(perception, sym), f"Missing export '{sym}' in skyvanta.perception"
        assert getattr(perception, sym) is not None


def test_modular_subpackage_exports():
    """Verify that modular subpackages export canonical classes."""
    import skyvanta.perception.detection as detection_pkg
    import skyvanta.perception.motion as motion_pkg
    import skyvanta.perception.fusion as fusion_pkg
    import skyvanta.perception.selection as selection_pkg

    assert hasattr(detection_pkg, "BaseDetector")
    assert hasattr(detection_pkg, "YoloDroneDetector")
    assert hasattr(motion_pkg, "MotionContrastDetector")
    assert hasattr(motion_pkg, "FarnebackOpticalFlow")
    assert hasattr(fusion_pkg, "CandidateFusion")
    assert hasattr(fusion_pkg, "CandidateFusionEngine")
    assert hasattr(fusion_pkg, "CandidateScorer")
    assert hasattr(selection_pkg, "TargetSelector")
