"""Unit tests for H3-02 YOLO offline execution, missing weights handling, and network blocking."""

import os
import pytest
import numpy as np
from skyvanta.core.config import DetectorConfig
from skyvanta.core.exceptions import ModelLoadError
from skyvanta.perception.detection.yolo import YoloDroneDetector


def test_yolo_disabled_by_config():
    """Verifies that use_yolo=False cleanly disables YOLO detector."""
    cfg = DetectorConfig(use_yolo=False)
    detector = YoloDroneDetector(cfg)
    assert detector.is_available is False
    assert detector.ok is False
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    assert detector.detect(frame) == []


def test_missing_local_model_raises_model_load_error_in_strict_mode():
    """Verifies strict mode raises ModelLoadError for non-existent weights when download is disabled."""
    cfg = DetectorConfig(
        use_yolo=True,
        yolo_model_path="non_existent_weights_xyz123.pt",
        allow_network_download=False,
    )
    with pytest.raises(ModelLoadError) as excinfo:
        YoloDroneDetector(cfg, strict=True)
    assert "allow_network_download is False" in str(excinfo.value) or "ultralytics" in str(excinfo.value)


def test_missing_local_model_graceful_fallback_in_default_mode():
    """Verifies non-strict mode falls back gracefully to unavailable without network calls."""
    cfg = DetectorConfig(
        use_yolo=True,
        yolo_model_path="non_existent_weights_xyz123.pt",
        allow_network_download=False,
    )
    detector = YoloDroneDetector(cfg, strict=False)
    assert detector.is_available is False
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    assert detector.detect(frame) == []


def test_default_config_disallows_network_download():
    """Verifies that DetectorConfig default has allow_network_download=False."""
    cfg = DetectorConfig()
    assert cfg.allow_network_download is False
