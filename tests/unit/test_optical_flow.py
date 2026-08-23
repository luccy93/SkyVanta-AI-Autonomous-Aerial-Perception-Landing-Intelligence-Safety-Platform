"""Unit tests for Farneback optical flow computation."""

import pytest
import numpy as np
import cv2
from skyvanta.core.config import OpticalFlowConfig
from skyvanta.core.types import BoundingBox
from skyvanta.perception.motion.optical_flow import FarnebackOpticalFlow


def test_optical_flow_first_frame():
    flow_engine = FarnebackOpticalFlow()
    frame1 = np.zeros((720, 1280, 3), dtype=np.uint8)
    res = flow_engine.compute(frame1)

    # First frame has no previous frame, should report no motion safely
    assert res.has_significant_motion is False
    assert res.mean_magnitude == 0.0


def test_optical_flow_static_scene():
    flow_engine = FarnebackOpticalFlow()
    frame = np.ones((720, 1280, 3), dtype=np.uint8) * 100
    flow_engine.compute(frame)
    res2 = flow_engine.compute(frame)

    assert res2.mean_magnitude < 0.1
    assert res2.has_significant_motion is False


def test_optical_flow_moving_target():
    flow_engine = FarnebackOpticalFlow()
    f1 = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.circle(f1, (300, 300), 40, (255, 255, 255), -1)

    f2 = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.circle(f2, (340, 300), 40, (255, 255, 255), -1)

    flow_engine.compute(f1)
    res = flow_engine.compute(f2)

    assert res.max_magnitude > 2.0
    assert res.has_significant_motion is True


def test_optical_flow_roi_energy():
    flow_engine = FarnebackOpticalFlow()
    f1 = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.rectangle(f1, (200, 200), (300, 300), (200, 200, 200), -1)
    flow_engine.compute(f1)

    box = BoundingBox(x1=200, y1=200, x2=300, y2=300)
    energy = flow_engine.extract_roi_flow_energy(box, (720, 1280))
    assert energy > 0.0
