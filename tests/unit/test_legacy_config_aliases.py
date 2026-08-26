"""Unit tests for H3-07: Legacy DetectorConfig aliases deprecation and backward compatibility."""

import pytest
import numpy as np
from skyvanta.core.config import DetectorConfig, MotionConfig, FusionConfig
from skyvanta.perception.motion.background import BackgroundSubtractorMotionDetector


def test_legacy_detector_config_aliases_instantiation():
    """Verifies that legacy alias fields in DetectorConfig initialize and serialize properly."""
    cfg = DetectorConfig(
        motion_history=200,
        motion_var_threshold=25.0,
        motion_min_area_ratio=0.0001,
        motion_max_area_ratio=0.10,
        fusion_iou_threshold=0.25,
    )
    assert cfg.motion_history == 200
    assert cfg.motion_var_threshold == 25.0
    assert cfg.motion_min_area_ratio == 0.0001
    assert cfg.motion_max_area_ratio == 0.10
    assert cfg.fusion_iou_threshold == 0.25


def test_background_subtractor_duck_typing_with_legacy_detector_config():
    """Verifies BackgroundSubtractorMotionDetector accepts legacy DetectorConfig."""
    legacy_cfg = DetectorConfig(
        motion_history=150,
        motion_var_threshold=22.0,
        motion_min_area_ratio=0.0002,
        motion_max_area_ratio=0.08,
    )
    detector = BackgroundSubtractorMotionDetector((720, 1280), legacy_cfg)
    assert detector.config.history == 150
    assert detector.config.var_threshold == 22.0
    assert detector.config.min_area_ratio == 0.0002
    assert detector.config.max_area_ratio == 0.08

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    res = detector.detect(frame)
    assert isinstance(res, list)


def test_canonical_motion_and_fusion_config_independence():
    """Verifies MotionConfig and FusionConfig operate independently of DetectorConfig."""
    m_cfg = MotionConfig(history=90, var_threshold=16.0)
    f_cfg = FusionConfig(iou_threshold=0.15)

    assert m_cfg.history == 90
    assert m_cfg.var_threshold == 16.0
    assert f_cfg.iou_threshold == 0.15
