"""Unit tests for spatial gating and IoU data association."""

import pytest
from skyvanta.core.config import AssociationConfig
from skyvanta.core.types import BoundingBox, Track, TrackLifecycleState
from skyvanta.tracking.association.gating import SpatialGater
from skyvanta.tracking.association.iou import IoUAssociator


def test_spatial_gater():
    gater = SpatialGater(AssociationConfig(max_center_distance_px=100.0, min_scale_ratio=0.5, max_scale_ratio=2.0))
    box1 = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)

    # Close box with similar size -> valid
    box_close = BoundingBox(x1=120.0, y1=120.0, x2=220.0, y2=220.0)
    assert gater.is_valid_pair(box1, box_close) is True

    # Distant box (>100px) -> invalid
    box_far = BoundingBox(x1=300.0, y1=300.0, x2=400.0, y2=400.0)
    assert gater.is_valid_pair(box1, box_far) is False

    # Huge scale difference -> invalid
    box_tiny = BoundingBox(x1=140.0, y1=140.0, x2=150.0, y2=150.0)
    assert gater.is_valid_pair(box1, box_tiny) is False


def test_iou_associator_matching():
    associator = IoUAssociator(AssociationConfig(min_iou=0.2))

    t1_box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    t2_box = BoundingBox(x1=400.0, y1=400.0, x2=500.0, y2=500.0)
    trk1 = Track(track_id=1, state=TrackLifecycleState.TRACKING, bbox=t1_box, predicted_bbox=t1_box)
    trk2 = Track(track_id=2, state=TrackLifecycleState.TRACKING, bbox=t2_box, predicted_bbox=t2_box)

    det1 = BoundingBox(x1=105.0, y1=105.0, x2=205.0, y2=205.0)  # Matches trk1
    det2 = BoundingBox(x1=395.0, y1=395.0, x2=495.0, y2=495.0)  # Matches trk2
    det3 = BoundingBox(x1=800.0, y1=800.0, x2=900.0, y2=900.0)  # Unmatched new detection

    matches, unmatched_tracks, unmatched_dets = associator.associate(
        tracks=[trk1, trk2],
        detections=[det1, det2, det3],
    )

    assert len(matches) == 2
    assert (0, 0) in matches  # trk1 -> det1
    assert (1, 1) in matches  # trk2 -> det2
    assert len(unmatched_tracks) == 0
    assert unmatched_dets == [2]  # det3 is unmatched


def test_iou_associator_unmatched_track():
    associator = IoUAssociator()
    t_box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    trk = Track(track_id=1, state=TrackLifecycleState.TRACKING, bbox=t_box, predicted_bbox=t_box)

    matches, unmatched_tracks, unmatched_dets = associator.associate(
        tracks=[trk],
        detections=[],
    )
    assert len(matches) == 0
    assert unmatched_tracks == [0]
    assert len(unmatched_dets) == 0


def test_iou_associator_perfect_and_zero_overlap():
    associator = IoUAssociator(AssociationConfig(min_iou=0.3))

    t_box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    trk = Track(track_id=1, state=TrackLifecycleState.TRACKING, bbox=t_box, predicted_bbox=t_box)

    # 1. Perfect overlap
    det_perfect = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    matches, unmatched_t, unmatched_d = associator.associate([trk], [det_perfect])
    assert matches == [(0, 0)]
    assert len(unmatched_t) == 0
    assert len(unmatched_d) == 0

    # 2. Zero overlap / disjoint
    det_disjoint = BoundingBox(x1=500.0, y1=500.0, x2=600.0, y2=600.0)
    matches_disj, unmatched_t_disj, unmatched_d_disj = associator.associate([trk], [det_disjoint])
    assert len(matches_disj) == 0
    assert unmatched_t_disj == [0]
    assert unmatched_d_disj == [0]


def test_iou_associator_competing_detections():
    associator = IoUAssociator(AssociationConfig(min_iou=0.2))

    t_box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)
    trk = Track(track_id=1, state=TrackLifecycleState.TRACKING, bbox=t_box, predicted_bbox=t_box)

    det_high_iou = BoundingBox(x1=105.0, y1=105.0, x2=205.0, y2=205.0)  # High IoU ~0.8
    det_low_iou = BoundingBox(x1=140.0, y1=140.0, x2=240.0, y2=240.0)   # Low IoU ~0.3

    matches, unmatched_t, unmatched_d = associator.associate([trk], [det_low_iou, det_high_iou])
    assert matches == [(0, 1)]  # Matched with det_high_iou at index 1
    assert len(unmatched_t) == 0
    assert unmatched_d == [0]   # det_low_iou at index 0 remains unmatched

