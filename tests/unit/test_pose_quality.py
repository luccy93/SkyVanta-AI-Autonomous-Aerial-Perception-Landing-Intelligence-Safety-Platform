"""Unit tests for pose quality evaluation."""

import pytest
from skyvanta.core.config import PoseQualityConfig
from skyvanta.target.quality import PoseQualityEvaluator


def test_high_quality_pose():
    evaluator = PoseQualityEvaluator(PoseQualityConfig())
    # 0.1px RMS error, large area 10000px², valid depth 2.0m, high detector confidence
    q = evaluator.evaluate(
        reprojection_error_rms=0.1,
        corner_area_px=10000.0,
        depth_m=2.0,
        detector_confidence=1.0,
    )
    assert q > 0.90
    assert q <= 1.0


def test_poor_quality_pose():
    evaluator = PoseQualityEvaluator(PoseQualityConfig(max_reproj_error_for_zero_quality=8.0))
    # 7.5px RMS error (near max cutoff), small area 50px²
    q = evaluator.evaluate(
        reprojection_error_rms=7.5,
        corner_area_px=50.0,
        depth_m=10.0,
        detector_confidence=0.5,
    )
    assert q < 0.35


def test_invalid_depth_zero_quality():
    evaluator = PoseQualityEvaluator()
    q = evaluator.evaluate(
        reprojection_error_rms=0.1,
        corner_area_px=5000.0,
        depth_m=-0.5,  # Negative depth
        detector_confidence=1.0,
    )
    assert q == 0.0
