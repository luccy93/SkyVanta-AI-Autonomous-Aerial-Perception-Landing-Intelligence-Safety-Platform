"""Unit tests for background subtractor motion detection."""

import pytest
import numpy as np
import cv2
from skyvanta.core.config import MotionConfig
from skyvanta.perception.motion.background import BackgroundSubtractorMotionDetector


def test_motion_detector_empty_static_scene():
    detector = BackgroundSubtractorMotionDetector((720, 1280))
    static_frame = np.ones((720, 1280, 3), dtype=np.uint8) * 128

    # Feed static frames
    for _ in range(5):
        cands = detector.detect(static_frame)

    # In static scene with no moving contrast, candidate list should be empty
    assert len(cands) == 0


def test_motion_detector_moving_blob():
    detector = BackgroundSubtractorMotionDetector((720, 1280))
    bg = np.zeros((720, 1280, 3), dtype=np.uint8)

    # Train background
    for _ in range(10):
        detector.detect(bg)

    # Inject moving contrasting blob in sky region
    moving_frame = bg.copy()
    cv2.rectangle(moving_frame, (500, 200), (600, 280), (255, 255, 255), -1)

    cands = detector.detect(moving_frame)
    assert len(cands) > 0
    best = cands[0]
    assert best.bbox.is_valid()
    assert best.motion_score > 0.0
    assert best.confidence > 0.0


def test_motion_detector_reset():
    detector = BackgroundSubtractorMotionDetector((720, 1280))
    detector.reset()
    assert detector.min_area > 0
