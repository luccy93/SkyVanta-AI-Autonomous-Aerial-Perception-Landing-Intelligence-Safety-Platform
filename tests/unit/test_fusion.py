"""Unit tests for CandidateFusionEngine and cross-association."""

import pytest
from skyvanta.core.types import BoundingBox, Detection, DetectionSource, MotionCandidate
from skyvanta.perception.fusion.candidate_fusion import CandidateFusionEngine


def test_fusion_yolo_and_motion_overlap():
    engine = CandidateFusionEngine()

    box_yolo = BoundingBox(x1=100, y1=100, x2=200, y2=200)
    box_motion = BoundingBox(x1=105, y1=105, x2=205, y2=205)

    det = Detection(bbox=box_yolo, confidence=0.85, class_name="drone", source=DetectionSource.YOLO)
    mot = MotionCandidate(bbox=box_motion, motion_score=800.0, confidence=0.6)

    fused = engine.fuse([det], [mot])
    assert len(fused) == 1
    c = fused[0]
    assert c.source == DetectionSource.YOLO_MOTION
    assert c.candidate_score > 0.6
    assert c.class_name == "drone"


def test_fusion_isolated_detections():
    engine = CandidateFusionEngine()

    box_yolo = BoundingBox(x1=100, y1=100, x2=200, y2=200)
    box_motion = BoundingBox(x1=500, y1=500, x2=600, y2=600)

    det = Detection(bbox=box_yolo, confidence=0.9, class_name="drone", source=DetectionSource.YOLO)
    mot = MotionCandidate(bbox=box_motion, motion_score=500.0, confidence=0.5)

    fused = engine.fuse([det], [mot])
    assert len(fused) == 2
    sources = [c.source for c in fused]
    assert DetectionSource.YOLO in sources
    assert DetectionSource.MOTION in sources


def test_fusion_empty():
    engine = CandidateFusionEngine()
    fused = engine.fuse([], [])
    assert len(fused) == 0
