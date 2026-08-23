"""Unit tests for Detection interface, MockDetector, and DetectionParser."""

import pytest
import numpy as np
from skyvanta.core.config import DetectorConfig
from skyvanta.core.exceptions import ModelLoadError
from skyvanta.core.types import BoundingBox, Detection, DetectionSource
from skyvanta.perception.detection.base import BaseDetector
from skyvanta.perception.detection.mock import MockDetector
from skyvanta.perception.detection.parser import DetectionParser
from skyvanta.perception.detection.yolo import YoloDroneDetector


def test_mock_detector_interface():
    box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    det = Detection(bbox=box, confidence=0.9, class_name="drone", source=DetectionSource.MOCK)
    mock = MockDetector(canned_detections=[det])

    assert isinstance(mock, BaseDetector)
    assert mock.is_available is True
    assert mock.get_info()["backend"] == "mock"

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    results = mock.detect(frame)
    assert len(results) == 1
    assert results[0].confidence == 0.9
    assert results[0].class_name == "drone"


def test_mock_detector_filtering():
    det1 = Detection(bbox=BoundingBox(x1=10, y1=10, x2=50, y2=50), confidence=0.3, source=DetectionSource.MOCK)
    det2 = Detection(bbox=BoundingBox(x1=60, y1=60, x2=100, y2=100), confidence=0.8, source=DetectionSource.MOCK)
    mock = MockDetector(canned_detections=[det1, det2])

    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    filtered = mock.detect(frame, confidence_threshold=0.5)
    assert len(filtered) == 1
    assert filtered[0].confidence == 0.8


def test_detection_parser():
    det = DetectionParser.parse_xyxy_box(
        x1=50, y1=60, x2=150, y2=160,
        confidence=0.88,
        class_name="airplane",
        class_id=1,
    )
    assert det is not None
    assert det.confidence == 0.88
    assert det.class_name == "airplane"
    assert det.bbox.width == 100
    assert det.bbox.height == 100

    # Invalid inverted box returns None
    invalid = DetectionParser.parse_xyxy_box(
        x1=150, y1=160, x2=50, y2=60,
        confidence=0.88,
    )
    assert invalid is None


def test_detection_parser_filters():
    d1 = Detection(bbox=BoundingBox(x1=0, y1=0, x2=10, y2=10), confidence=0.4, class_name="bird")
    d2 = Detection(bbox=BoundingBox(x1=0, y1=0, x2=10, y2=10), confidence=0.9, class_name="drone")

    by_class = DetectionParser.filter_by_class([d1, d2], allowed_classes={"drone"})
    assert len(by_class) == 1
    assert by_class[0].class_name == "drone"

    by_conf = DetectionParser.filter_by_confidence([d1, d2], min_confidence=0.5)
    assert len(by_conf) == 1
    assert by_conf[0].confidence == 0.9


def test_yolo_strict_missing_model():
    cfg = DetectorConfig(use_yolo=True, yolo_model_path="non_existent_weights_12345.pt")
    # If ultralytics is present, strict mode will raise ModelLoadError
    # If ultralytics is not present, strict mode will also raise ModelLoadError
    with pytest.raises(ModelLoadError):
        YoloDroneDetector(config=cfg, strict=True)
