"""Spatial localization service, camera extrinsics integration, and multi-frame pose resolution."""

import math
from typing import Optional, Union
import numpy as np

from skyvanta.core.config import CameraExtrinsicsConfig, SpatialConfig
from skyvanta.core.exceptions import DisconnectedFrameError
from skyvanta.core.logging import get_logger
from skyvanta.core.types import FrameId, Pose6D, PoseEstimateResult, SpatialLocalizationResult
from skyvanta.spatial.frame_graph import FrameGraph
from skyvanta.spatial.se3 import SE3Transform
from skyvanta.spatial.transform import euler_to_rotation_matrix, quaternion_to_rotation_matrix

logger = get_logger("skyvanta.spatial.localization")


class SpatialLocalizationService:
    """Orchestrates spatial coordinate frame transformations and target localization relative to drone body and world."""

    def __init__(
        self,
        config: Optional[SpatialConfig] = None,
        frame_graph: Optional[FrameGraph] = None,
    ):
        self.config = config or SpatialConfig()
        self.frame_graph = frame_graph or FrameGraph()

        # Initialize static camera extrinsics
        self._init_camera_extrinsics()

    def _init_camera_extrinsics(self) -> None:
        """Registers the static body-to-camera extrinsic mounting transform."""
        ext_cfg: CameraExtrinsicsConfig = self.config.camera_extrinsics
        if not ext_cfg.enabled:
            return

        parent = FrameId(ext_cfg.parent_frame)
        child = FrameId(ext_cfg.child_frame)

        if ext_cfg.rotation_quaternion is not None and len(ext_cfg.rotation_quaternion) == 4:
            qw, qx, qy, qz = ext_cfg.rotation_quaternion
            R = quaternion_to_rotation_matrix((qw, qx, qy, qz))
        else:
            r, p, y = ext_cfg.rotation_rpy_deg
            R = euler_to_rotation_matrix(math.radians(r), math.radians(p), math.radians(y))

        t = np.array(ext_cfg.translation_m, dtype=np.float64)

        # T_parent_child maps points from camera frame into body frame: p_body = R * p_cam + t
        transform_body_cam = SE3Transform(
            source_frame=child,
            target_frame=parent,
            rotation=R,
            translation=t,
            is_static=True,
        )
        self.frame_graph.add_transform(transform_body_cam)
        logger.info("Registered static extrinsic transform T_%s_%s", parent.value, child.value)

    def register_world_reference(
        self,
        transform_world_body: SE3Transform,
    ) -> None:
        """Registers an external metric world-to-body navigation transform (e.g. from future GPS, SLAM, or VIO)."""
        if transform_world_body.source_frame != FrameId.BODY or transform_world_body.target_frame != FrameId.WORLD:
            logger.warning(
                "World reference transform should map source=BODY to target=WORLD, received %s -> %s",
                transform_world_body.source_frame.value,
                transform_world_body.target_frame.value,
            )
        self.frame_graph.add_transform(transform_world_body)

    def localize_target(
        self,
        pose_result: PoseEstimateResult,
        target_frame: Union[FrameId, str] = FrameId.BODY,
    ) -> SpatialLocalizationResult:
        """Transforms a camera-relative landing pad pose estimate into the requested target frame (default: BODY).

        Args:
            pose_result: V4 PoseEstimateResult expressing T_camera_pad.
            target_frame: Desired destination coordinate frame (BODY, WORLD, etc.).

        Returns:
            SpatialLocalizationResult with transformed pose or explicit failure reason.
        """
        tgt = FrameId(target_frame) if isinstance(target_frame, str) else target_frame

        if not pose_result.is_valid or pose_result.pose is None:
            return SpatialLocalizationResult(
                target_id=pose_result.target_id,
                source_frame=FrameId.CAMERA,
                target_frame=tgt,
                pose=None,
                timestamp_sec=pose_result.timestamp_sec,
                is_valid=False,
                is_world_relative=False,
                failure_reason=f"Input pose estimate is invalid: {pose_result.failure_reason}",
            )

        # Register the dynamic measurement T_camera_pad in the frame graph
        transform_cam_pad = SE3Transform.from_pose6d(
            pose=pose_result.pose,
            source_frame=FrameId.LANDING_PAD,
            target_frame=FrameId.CAMERA,
            is_static=False,
        )
        self.frame_graph.add_transform(transform_cam_pad)

        # Transform from CAMERA to target_frame
        try:
            return self.frame_graph.transform_pose(
                pose=pose_result.pose,
                source_frame=FrameId.CAMERA,
                target_frame=tgt,
                timestamp_sec=pose_result.timestamp_sec,
            )
        except DisconnectedFrameError as e:
            is_world_query = (tgt == FrameId.WORLD)
            reason = (
                "WORLD frame reference is unavailable (no GPS, SLAM, or external visual odometry registered)"
                if is_world_query else str(e)
            )
            return SpatialLocalizationResult(
                target_id=pose_result.target_id,
                source_frame=FrameId.CAMERA,
                target_frame=tgt,
                pose=None,
                timestamp_sec=pose_result.timestamp_sec,
                is_valid=False,
                is_world_relative=False,
                failure_reason=reason,
            )
