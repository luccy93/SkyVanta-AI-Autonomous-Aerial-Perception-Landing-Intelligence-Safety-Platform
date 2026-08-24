"""Unit tests for FrameGraph, transform registry, and shortest-path SE(3) composition."""

import pytest
import numpy as np

from skyvanta.core.exceptions import DisconnectedFrameError, FrameError, TransformLookupError
from skyvanta.core.types import FrameId, Pose6D
from skyvanta.spatial.frame_graph import FrameGraph
from skyvanta.spatial.se3 import SE3Transform


def test_frame_graph_direct_and_inverse_lookup():
    graph = FrameGraph()

    t_body_cam = SE3Transform.from_euler(
        source_frame=FrameId.CAMERA,
        target_frame=FrameId.BODY,
        translation=(0.15, 0.0, -0.05),
        euler_deg=(0.0, 90.0, 0.0),
    )
    graph.add_transform(t_body_cam)

    # Direct lookup: CAMERA -> BODY
    direct = graph.lookup_transform(FrameId.CAMERA, FrameId.BODY)
    assert direct.source_frame == FrameId.CAMERA
    assert direct.target_frame == FrameId.BODY
    assert np.allclose(direct.to_matrix(), t_body_cam.to_matrix())

    # Inverse lookup: BODY -> CAMERA
    inv = graph.lookup_transform(FrameId.BODY, FrameId.CAMERA)
    assert inv.source_frame == FrameId.BODY
    assert inv.target_frame == FrameId.CAMERA
    assert np.allclose(inv.to_matrix(), t_body_cam.inverse().to_matrix())


def test_frame_graph_multi_hop_chain():
    graph = FrameGraph()

    # T_body_cam
    t_body_cam = SE3Transform.from_euler(
        source_frame=FrameId.CAMERA,
        target_frame=FrameId.BODY,
        translation=(0.20, 0.0, -0.10),
        euler_deg=(0.0, 0.0, 0.0),
    )
    # T_cam_pad
    t_cam_pad = SE3Transform.from_euler(
        source_frame=FrameId.LANDING_PAD,
        target_frame=FrameId.CAMERA,
        translation=(0.0, 0.0, 2.0),
        euler_deg=(0.0, 0.0, 0.0),
    )

    graph.add_transform(t_body_cam)
    graph.add_transform(t_cam_pad)

    # Multi-hop lookup: LANDING_PAD -> BODY
    composed = graph.lookup_transform(FrameId.LANDING_PAD, FrameId.BODY)
    assert composed.source_frame == FrameId.LANDING_PAD
    assert composed.target_frame == FrameId.BODY

    # [0, 0, 2] in CAM + [0.2, 0, -0.1] = [0.2, 0, 1.9] in BODY
    assert np.allclose(composed.translation, [0.20, 0.0, 1.90])


def test_frame_graph_disconnected_frame():
    graph = FrameGraph()

    # Only register BODY <-> CAMERA
    t_body_cam = SE3Transform.identity(FrameId.BODY)
    t_body_cam.source_frame = FrameId.CAMERA
    graph.add_transform(t_body_cam)

    # Query CAMERA -> WORLD (WORLD is disconnected)
    with pytest.raises(DisconnectedFrameError, match="has no registered transforms"):
        graph.lookup_transform(FrameId.CAMERA, FrameId.WORLD)


def test_frame_graph_identical_frame_identity():
    graph = FrameGraph()
    t_ident = graph.lookup_transform(FrameId.BODY, FrameId.BODY)
    assert t_ident.source_frame == FrameId.BODY
    assert t_ident.target_frame == FrameId.BODY
    assert np.allclose(t_ident.to_matrix(), np.eye(4))


def test_frame_graph_stale_dynamic_transform():
    graph = FrameGraph()

    # Dynamic transform with timestamp 10.0s
    t_dynamic = SE3Transform.from_euler(
        source_frame=FrameId.LANDING_PAD,
        target_frame=FrameId.CAMERA,
        translation=(0.0, 0.0, 1.0),
        euler_deg=(0.0, 0.0, 0.0),
        timestamp_sec=10.0,
        is_static=False,
    )
    graph.add_transform(t_dynamic)

    # Query with timestamp 12.0s and max_age 0.5s -> should raise TransformLookupError
    with pytest.raises(TransformLookupError, match="stale"):
        graph.lookup_transform(FrameId.LANDING_PAD, FrameId.CAMERA, timestamp_sec=12.0, max_age_sec=0.5)
