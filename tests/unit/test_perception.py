"""Unit tests for MotionContrastDetector and CandidateFusion."""

import pytest
import numpy as np
import cv2
from skyvanta.core.types import BoundingBox, Detection
from skyvanta.perception.fusion import CandidateFusion
from skyvanta.perception.motion import MotionContrastDetector


def test_candidate_fusion_overlapping_boxes():
    fusion = CandidateFusion()
    yolo_box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    motion_box = BoundingBox(x1=105.0, y1=105.0, x2=205.0, y2=205.0)

    yolo_dets = [Detection(bbox=yolo_box, confidence=0.8, class_name="drone", source="yolo")]
    motion_dets = [Detection(bbox=motion_box, confidence=0.6, class_name="motion_target", source="motion")]

    fused_box, conf = fusion.pick_best(yolo_dets, motion_dets)
    assert fused_box is not None
    assert conf == 0.90
    # Center should be averaged
    assert fused_box.x1 == 102.5
    assert fused_box.y1 == 102.5


def test_candidate_fusion_empty():
    fusion = CandidateFusion()
    fused_box, conf = fusion.pick_best([], [])
    assert fused_box is None
    assert conf == 0.0


def test_motion_detector_runs():
    detector = MotionContrastDetector((720, 1280))
    frame1 = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame2 = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.circle(frame2, (640, 360), 30, (255, 255, 255), -1)

    dets1 = detector.detect(frame1)
    dets2 = detector.detect(frame2)
    assert isinstance(dets1, list)
    assert isinstance(dets2, list)
