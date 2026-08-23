"""Unit tests for SkyVanta configuration serialization and defaults."""

import os
import tempfile
import pytest
from skyvanta.core.config import SkyVantaConfig


def test_default_config_creation():
    cfg = SkyVantaConfig()
    assert cfg.detector.use_yolo is True
    assert cfg.detector.yolo_confidence_threshold == 0.08
    assert cfg.tracker.max_lost_frames == 45
    assert cfg.pipeline.max_dimension == 1280


def test_yaml_roundtrip():
    cfg = SkyVantaConfig()
    cfg.detector.yolo_confidence_threshold = 0.25
    cfg.tracker.max_lost_frames = 60

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = os.path.join(tmpdir, "test_config.yaml")
        cfg.to_yaml(tmp_path)
        assert os.path.exists(tmp_path)

        loaded_cfg = SkyVantaConfig.from_yaml(tmp_path)
        assert loaded_cfg.detector.yolo_confidence_threshold == 0.25
        assert loaded_cfg.tracker.max_lost_frames == 60
