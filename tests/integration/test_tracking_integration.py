"""Deterministic integration test for Multi-Target Tracking & State Estimation (Volume 3)."""

import pytest
from skyvanta.core.config import SkyVantaConfig, TrackingConfig
from skyvanta.core.types import (
    BoundingBox,
    Candidate,
    DetectionSource,
    PerceptionFrameResult,
    TrackLifecycleState,
)
from skyvanta.tracking.manager import MultiTargetTrackManager


def test_tracking_engine_full_lifecycle_and_recovery():
    """Verifies target initialization, steady tracking, occlusion coasting, and track recovery."""
    manager = MultiTargetTrackManager()

    # Phase 1: 5 frames of steady target movement (cx: 200 -> 240)
    for i in range(5):
        cx = 200.0 + i * 10.0
        cy = 150.0 + i * 5.0
        box = BoundingBox(x1=cx - 30, y1=cy - 20, x2=cx + 30, y2=cy + 20)
        cand = Candidate(bbox=box, candidate_score=0.90, source=DetectionSource.YOLO)
        p_res = PerceptionFrameResult(frame_id=i, timestamp_sec=i * 0.033, fused_candidates=[cand])
        res = manager.process(p_res)

        assert len(res.tracks) == 1
        assert res.tracks[0].track_id == 1
        if i >= 2:
            assert res.tracks[0].state in (TrackLifecycleState.CONFIRMED, TrackLifecycleState.TRACKING)

    # Phase 2: 3 frames of occlusion (no detections) -> track enters COASTING
    for i in range(5, 8):
        p_res_empty = PerceptionFrameResult(frame_id=i, timestamp_sec=i * 0.033, fused_candidates=[])
        res = manager.process(p_res_empty)

        assert len(res.tracks) == 1
        trk = res.tracks[0]
        assert trk.track_id == 1
        assert trk.state == TrackLifecycleState.COASTING
        # Prediction continues moving forward
        assert trk.bbox.center[0] > 230.0

    # Phase 3: Target reappears at frame 8 -> track RECOVERS to TRACKING with same ID!
    box_recovered = BoundingBox(x1=280 - 30, y1=190 - 20, x2=280 + 30, y2=190 + 20)
    cand_rec = Candidate(bbox=box_recovered, candidate_score=0.92, source=DetectionSource.YOLO)
    res_rec = manager.process(PerceptionFrameResult(frame_id=8, timestamp_sec=8 * 0.033, fused_candidates=[cand_rec]))

    assert len(res_rec.tracks) == 1
    recovered_track = res_rec.tracks[0]
    assert recovered_track.track_id == 1  # Retained same track identity!
    assert recovered_track.state == TrackLifecycleState.TRACKING
    assert len(res_rec.confirmed_tracks) == 1
    assert res_rec.timing.total_ms > 0.0


def test_tracking_engine_simultaneous_multi_target():
    """Verifies tracking of 3 distinct targets simultaneously without ID switching."""
    manager = MultiTargetTrackManager()

    # Track 3 moving targets for 10 frames
    for i in range(10):
        # Target 1: moving right
        box1 = BoundingBox(x1=100 + i * 5, y1=100, x2=160 + i * 5, y2=160)
        cand1 = Candidate(bbox=box1, candidate_score=0.88, source=DetectionSource.YOLO)

        # Target 2: moving down
        box2 = BoundingBox(x1=500, y1=200 + i * 8, x2=560, y2=260 + i * 8)
        cand2 = Candidate(bbox=box2, candidate_score=0.85, source=DetectionSource.YOLO)

        # Target 3: moving diagonally
        box3 = BoundingBox(x1=800 - i * 6, y1=400 + i * 4, x2=860 - i * 6, y2=460 + i * 4)
        cand3 = Candidate(bbox=box3, candidate_score=0.82, source=DetectionSource.MOTION)

        p_res = PerceptionFrameResult(frame_id=i, timestamp_sec=i * 0.033, fused_candidates=[cand1, cand2, cand3])
        res = manager.process(p_res)

        assert len(res.tracks) == 3
        # After warm-up, all 3 targets should be confirmed
        if i >= 3:
            assert len(res.confirmed_tracks) == 3
            # Ensure unique IDs {1, 2, 3}
            track_ids = {t.track_id for t in res.tracks}
            assert track_ids == {1, 2, 3}


def test_tracking_engine_crossing_trajectories():
    """Verifies that two targets crossing paths retain active tracking status."""
    manager = MultiTargetTrackManager()

    # Target 1 starts left (x=100) moving right (+20 px/frame)
    # Target 2 starts right (x=500) moving left (-20 px/frame)
    # They cross near x=300 at frame 10
    for i in range(20):
        t1_x = 100.0 + i * 20.0
        t2_x = 500.0 - i * 20.0
        
        b1 = BoundingBox(x1=t1_x - 20, y1=200 - 20, x2=t1_x + 20, y2=200 + 20)
        b2 = BoundingBox(x1=t2_x - 20, y1=200 - 20, x2=t2_x + 20, y2=200 + 20)
        
        c1 = Candidate(bbox=b1, candidate_score=0.90, source=DetectionSource.YOLO)
        c2 = Candidate(bbox=b2, candidate_score=0.90, source=DetectionSource.YOLO)

        res = manager.process(PerceptionFrameResult(frame_id=i, timestamp_sec=i * 0.033, fused_candidates=[c1, c2]))
        assert len(res.tracks) == 2

