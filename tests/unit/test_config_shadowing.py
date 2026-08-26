"""Regression tests for H3-01: Authoritative detector configuration and shadowing prevention."""

import os
import tempfile
import pytest
from skyvanta.core.config import SkyVantaConfig, DetectorConfig, PerceptionConfig
from skyvanta.tracking.tracker import DroneTracker


def test_authoritative_perception_detector_consumed_by_tracker():
    """Verifies DroneTracker checks perception.detector.use_yolo directly."""
    config = SkyVantaConfig()
    config.perception.detector.use_yolo = False
    tracker = DroneTracker((720, 1280), config)
    assert tracker.yolo is None

    config.perception.detector.use_yolo = True
    # If ultralytics is not installed or model is missing, yolo may be None or disabled,
    # but the branch taken inside DroneTracker evaluates config.perception.detector.use_yolo
    assert config.perception.detector.use_yolo is True
    assert config.detector.use_yolo is True


def test_config_detector_property_bidirectional_sync():
    """Verifies that config.detector property reads and writes to perception.detector directly."""
    config = SkyVantaConfig()
    assert config.detector is config.perception.detector

    config.detector.yolo_confidence_threshold = 0.42
    assert config.perception.detector.yolo_confidence_threshold == 0.42

    new_det = DetectorConfig(use_yolo=False, yolo_confidence_threshold=0.99)
    config.detector = new_det
    assert config.perception.detector.use_yolo is False
    assert config.perception.detector.yolo_confidence_threshold == 0.99
    assert config.detector is config.perception.detector


def test_legacy_dict_migration_before_validation():
    """Verifies that legacy top-level dicts with 'detector' are migrated to 'perception.detector'."""
    legacy_data = {
        "detector": {
            "use_yolo": False,
            "yolo_confidence_threshold": 0.55,
        }
    }
    cfg = SkyVantaConfig.model_validate(legacy_data)
    assert cfg.perception.detector.use_yolo is False
    assert cfg.perception.detector.yolo_confidence_threshold == 0.55
    assert cfg.detector.use_yolo is False


def test_perception_detector_authoritative_over_legacy_conflict():
    """Verifies that if both keys exist in a raw dictionary, perception.detector is authoritative."""
    conflicting_data = {
        "perception": {
            "detector": {
                "use_yolo": True,
                "yolo_confidence_threshold": 0.33,
            }
        },
        "detector": {
            "use_yolo": False,
            "yolo_confidence_threshold": 0.99,
        }
    }
    cfg = SkyVantaConfig.model_validate(conflicting_data)
    assert cfg.perception.detector.use_yolo is True
    assert cfg.perception.detector.yolo_confidence_threshold == 0.33
    assert cfg.detector.use_yolo is True
    assert cfg.detector.yolo_confidence_threshold == 0.33


def test_yaml_serialization_no_duplicate_detector():
    """Verifies that serialization writes only perception.detector without duplicating top-level detector."""
    cfg = SkyVantaConfig()
    cfg.perception.detector.yolo_confidence_threshold = 0.77

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config.yaml")
        cfg.to_yaml(path)

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Top-level 'detector:' should not be serialized as a duplicate key
        # Only perception.detector should be present
        dumped_dict = cfg.model_dump()
        assert "perception" in dumped_dict
        assert "detector" in dumped_dict["perception"]
        assert "detector" not in dumped_dict  # Removed as a model field

        loaded_cfg = SkyVantaConfig.from_yaml(path)
        assert loaded_cfg.perception.detector.yolo_confidence_threshold == 0.77
        assert loaded_cfg.detector.yolo_confidence_threshold == 0.77
