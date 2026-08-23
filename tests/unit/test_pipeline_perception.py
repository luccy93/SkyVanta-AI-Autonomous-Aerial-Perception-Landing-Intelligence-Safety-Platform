"""Unit tests for PerceptionPipeline orchestration and latency instrumentation."""

import pytest
import numpy as np
from skyvanta.core.config import PerceptionConfig
from skyvanta.core.types import BoundingBox, Detection, DetectionSource
from skyvanta.perception.detection.mock import MockDetector
from skyvanta.perception.pipeline import PerceptionPipeline


def test_perception_pipeline_mock_flow():
    cfg = PerceptionConfig()
    box = BoundingBox(x1=200, y1=200, x2=300, y2=300)
    det = Detection(bbox=box, confidence=0.92, class_name="drone", source=DetectionSource.MOCK)
    mock_det = MockDetector(canned_detections=[det])

    pipeline = PerceptionPipeline(frame_shape=(720, 1280), config=cfg, detector=mock_det)

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    res = pipeline.process(frame, frame_id=1, timestamp_sec=0.033)

    assert res.is_valid_frame is True
    assert res.frame_id == 1
    assert len(res.detections) == 1
    assert res.selected_target is not None
    assert res.selected_target.class_name == "drone"

    # Verify timing instrumentation
    assert res.timing.total_ms > 0.0
    assert res.timing.detection_ms >= 0.0
    assert res.timing.validation_ms >= 0.0


def test_perception_pipeline_invalid_frame():
    pipeline = PerceptionPipeline(frame_shape=(720, 1280))
    res = pipeline.process(None, frame_id=0)

    assert res.is_valid_frame is False
    assert res.selected_target is None
    assert "validation_error" in res.diagnostics
