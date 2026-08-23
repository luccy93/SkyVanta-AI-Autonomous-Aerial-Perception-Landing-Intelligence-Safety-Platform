"""Unit tests for TargetSelector heuristics."""

import pytest
from skyvanta.core.config import TargetSelectionConfig
from skyvanta.core.types import BoundingBox, Candidate, DetectionSource
from skyvanta.perception.selection.target_selector import TargetSelector


def test_target_selector_empty():
    selector = TargetSelector()
    res = selector.select([])
    assert res is None


def test_target_selector_ranking():
    selector = TargetSelector()

    c1 = Candidate(
        bbox=BoundingBox(x1=100, y1=100, x2=200, y2=200),
        candidate_score=0.45,
        source=DetectionSource.MOTION,
    )
    c2 = Candidate(
        bbox=BoundingBox(x1=300, y1=300, x2=400, y2=400),
        candidate_score=0.85,
        source=DetectionSource.YOLO_MOTION,
    )

    selected = selector.select([c2, c1], frame_shape=(720, 1280))
    assert selected is not None
    assert selected.candidate_score == 0.85
    assert selected.bbox.x1 == 300


def test_target_selector_filter_low_score():
    cfg = TargetSelectionConfig(min_candidate_score=0.50)
    selector = TargetSelector(cfg)

    c = Candidate(
        bbox=BoundingBox(x1=100, y1=100, x2=200, y2=200),
        candidate_score=0.35,
        source=DetectionSource.MOTION,
    )
    selected = selector.select([c])
    assert selected is None
