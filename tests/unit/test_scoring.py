"""Unit tests for CandidateScorer formula and weighting."""

import pytest
from skyvanta.core.config import FusionConfig
from skyvanta.perception.fusion.scoring import CandidateScorer


def test_scorer_basic_weights():
    cfg = FusionConfig(
        weight_detection=0.5,
        weight_motion=0.3,
        weight_flow=0.1,
        weight_iou=0.1,
    )
    scorer = CandidateScorer(cfg)

    # Isolated YOLO detection with 0.8 conf
    score_yolo = scorer.score(det_conf=0.8, mot_conf=0.0, flow_conf=0.0, iou=0.0)
    assert pytest.approx(score_yolo) == 0.5 * 0.8  # 0.40

    # Overlapping YOLO + Motion detection
    score_overlap = scorer.score(det_conf=0.8, mot_conf=0.6, flow_conf=0.5, iou=0.8)
    assert score_overlap > score_yolo
    assert score_overlap <= 1.0


def test_scorer_clamp():
    scorer = CandidateScorer()
    score = scorer.score(det_conf=1.0, mot_conf=1.0, flow_conf=1.0, iou=1.0)
    assert score <= 1.0
    assert score >= 0.0
