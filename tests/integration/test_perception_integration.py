"""Deterministic integration test for the complete Perception Engine (Volume 2)."""

import pytest
import numpy as np
import cv2
from skyvanta.core.config import PerceptionConfig
from skyvanta.core.types import BoundingBox, Detection, DetectionSource
from skyvanta.perception.detection.mock import MockDetector
from skyvanta.perception.pipeline import PerceptionPipeline


def test_perception_engine_end_to_end_deterministic():
    """Verifies that synthetic frames feed through all perception modules and produce a valid PerceptionFrameResult."""
    # Build synthetic moving frame sequence
    frames = []
    for i in range(10):
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        # Add background structure
        cv2.line(img, (0, 300), (1280, 300), (40, 40, 40), 2)
        # Add moving target in sky
        cx, cy = 400 + i * 20, 200 + i * 5
        cv2.rectangle(img, (cx - 30, cy - 20), (cx + 30, cy + 20), (220, 220, 220), -1)
        frames.append((img, (cx, cy)))

    # Setup deterministic mock detector returning position for each frame
    def mock_generator(frame: np.ndarray, frame_id: int):
        if frame_id is not None and frame_id < len(frames):
            _, (cx, cy) = frames[frame_id]
            box = BoundingBox(x1=cx - 30, y1=cy - 20, x2=cx + 30, y2=cy + 20)
            return [Detection(bbox=box, confidence=0.88, class_name="drone", source=DetectionSource.MOCK)]
        return []

    mock_detector = MockDetector(generator_fn=mock_generator)
    config = PerceptionConfig()
    pipeline = PerceptionPipeline(
        frame_shape=(720, 1280),
        config=config,
        detector=mock_detector,
    )

    results = []
    for i, (frame, (expected_cx, expected_cy)) in enumerate(frames):
        res = pipeline.process(frame, frame_id=i, timestamp_sec=i / 30.0)
        results.append(res)

        assert res.is_valid_frame is True
        assert res.frame_id == i
        assert len(res.detections) == 1
        assert res.timing.total_ms > 0.0

        # After first frame, optical flow and motion should detect the target
        if i >= 1:
            assert res.selected_target is not None
            assert res.selected_target.bbox.is_valid()
            # Selected target center should be close to expected position
            sel_cx, sel_cy = res.selected_target.bbox.center
            assert pytest.approx(sel_cx, abs=15.0) == expected_cx
            assert pytest.approx(sel_cy, abs=15.0) == expected_cy

    assert len(results) == 10
