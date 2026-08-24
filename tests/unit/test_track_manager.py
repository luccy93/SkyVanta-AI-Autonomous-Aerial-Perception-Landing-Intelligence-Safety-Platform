"""Unit tests for MultiTargetTrackManager."""

import pytest
from skyvanta.core.config import TrackingConfig
from skyvanta.core.types import (
    BoundingBox,
    Candidate,
    DetectionSource,
    PerceptionFrameResult,
    TrackLifecycleState,
)
from skyvanta.tracking.manager import MultiTargetTrackManager


def test_track_manager_single_target_lifecycle():
    manager = MultiTargetTrackManager()

    # Frame 0: Initial detection -> creates TENTATIVE track
    box0 = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    cand0 = Candidate(bbox=box0, candidate_score=0.85, source=DetectionSource.YOLO)
    p_res0 = PerceptionFrameResult(frame_id=0, timestamp_sec=0.0, fused_candidates=[cand0])

    res0 = manager.process(p_res0)
    assert len(res0.tracks) == 1
    t0 = res0.tracks[0]
    assert t0.state == TrackLifecycleState.TENTATIVE
    assert t0.track_id == 1

    # Frames 1 & 2: Hits -> transitions to CONFIRMED
    for i in (1, 2):
        box_i = BoundingBox(x1=100.0 + i * 5, y1=100.0, x2=200.0 + i * 5, y2=200.0)
        cand_i = Candidate(bbox=box_i, candidate_score=0.85, source=DetectionSource.YOLO)
        res_i = manager.process(PerceptionFrameResult(frame_id=i, timestamp_sec=i * 0.033, fused_candidates=[cand_i]))

    assert len(res_i.confirmed_tracks) == 1
    assert res_i.confirmed_tracks[0].track_id == 1


def test_track_manager_multi_target_stable_ids():
    manager = MultiTargetTrackManager()

    # Frame 0: Two targets
    cand_a = Candidate(bbox=BoundingBox(x1=100, y1=100, x2=200, y2=200), candidate_score=0.8, source=DetectionSource.YOLO)
    cand_b = Candidate(bbox=BoundingBox(x1=500, y1=500, x2=600, y2=600), candidate_score=0.8, source=DetectionSource.YOLO)
    res0 = manager.process(PerceptionFrameResult(frame_id=0, timestamp_sec=0.0, fused_candidates=[cand_a, cand_b]))

    assert len(res0.tracks) == 2
    ids_0 = {t.track_id for t in res0.tracks}
    assert len(ids_0) == 2

    # Frame 1: Both targets moved slightly
    cand_a1 = Candidate(bbox=BoundingBox(x1=105, y1=102, x2=205, y2=202), candidate_score=0.8, source=DetectionSource.YOLO)
    cand_b1 = Candidate(bbox=BoundingBox(x1=505, y1=502, x2=605, y2=602), candidate_score=0.8, source=DetectionSource.YOLO)
    res1 = manager.process(PerceptionFrameResult(frame_id=1, timestamp_sec=0.033, fused_candidates=[cand_a1, cand_b1]))

    assert len(res1.tracks) == 2
    ids_1 = {t.track_id for t in res1.tracks}
    # Track IDs must remain completely stable!
    assert ids_0 == ids_1


def test_track_manager_quality_and_get_track():
    manager = MultiTargetTrackManager()
    box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    cand = Candidate(bbox=box, candidate_score=0.95, source=DetectionSource.YOLO)
    
    # 5 successful hits -> high quality
    for i in range(5):
        manager.process(PerceptionFrameResult(frame_id=i, timestamp_sec=i * 0.033, fused_candidates=[cand]))

    trk = manager.get_track(1)
    assert trk is not None
    assert trk.track_id == 1
    assert trk.hits == 5
    assert trk.track_quality > 0.80

    # Non-existent track ID
    assert manager.get_track(999) is None


def test_track_manager_reset():
    manager = MultiTargetTrackManager()
    box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    cand = Candidate(bbox=box, candidate_score=0.9, source=DetectionSource.YOLO)
    manager.process(PerceptionFrameResult(frame_id=0, timestamp_sec=0.0, fused_candidates=[cand]))
    assert len(manager.process(PerceptionFrameResult(frame_id=1, timestamp_sec=0.033, fused_candidates=[cand])).tracks) == 1

    manager.reset()
    assert manager.get_track(1) is None

