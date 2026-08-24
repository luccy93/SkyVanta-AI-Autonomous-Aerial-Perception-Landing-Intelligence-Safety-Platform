"""End-to-end spatial landing target detector and 6-DoF PnP pose estimation pipeline."""

from typing import List, Optional, Tuple
import numpy as np

from skyvanta.core.config import LandingTargetConfig
from skyvanta.core.logging import get_logger
from skyvanta.core.types import LandingPad, LandingTarget, PoseEstimateResult
from skyvanta.spatial.camera import CameraModel
from skyvanta.spatial.pnp import PnPPoseSolver
from skyvanta.target.base import BaseFiducialDetector
from skyvanta.target.factory import FiducialDetectorFactory
from skyvanta.target.geometry import TargetGeometry
from skyvanta.target.quality import PoseQualityEvaluator
from skyvanta.target.validation import CornerValidator

logger = get_logger("skyvanta.target.estimator")


class SpatialLandingPadEstimator:
    """Orchestrates landing-pad fiducial detection, corner validation, and 6-DoF PnP pose estimation."""

    def __init__(
        self,
        config: Optional[LandingTargetConfig] = None,
        camera_model: Optional[CameraModel] = None,
        detector: Optional[BaseFiducialDetector] = None,
    ):
        self.config = config or LandingTargetConfig()
        self.camera_model = camera_model or CameraModel(self.config.camera)
        self.detector = detector or FiducialDetectorFactory.create(self.config)

        # Geometric and solver sub-components
        marker_size = self.config.aruco.marker_size_m if self.config.detector_type == "aruco" else self.config.april_tag.tag_size_m
        self.geometry = TargetGeometry(marker_size)
        self.validator = CornerValidator(min_area_px=self.config.quality.min_corner_area_px)
        self.pnp_solver = PnPPoseSolver(self.config.pnp, self.config.quality)
        self.quality_evaluator = PoseQualityEvaluator(self.config.quality)

        self._frame_count = 0

    def process(
        self,
        frame_bgr: np.ndarray,
        timestamp_sec: Optional[float] = None,
        frame_id: Optional[int] = None,
    ) -> Tuple[List[LandingTarget], Optional[PoseEstimateResult], Optional[LandingPad]]:
        """Executes full spatial detection and 6-DoF PnP estimation on a video frame.

        Args:
            frame_bgr: Video frame image array.
            timestamp_sec: Capture timestamp in seconds.
            frame_id: Frame sequence index.

        Returns:
            (detected_targets, primary_pose_result, unified_landing_pad)
        """
        fid = frame_id if frame_id is not None else self._frame_count
        t_sec = timestamp_sec if timestamp_sec is not None else (fid / 30.0)
        self._frame_count += 1

        if not self.config.enabled or frame_bgr is None or frame_bgr.size == 0:
            return [], None, None

        # Step 1: Detect Fiducials
        targets = self.detector.detect(frame_bgr, timestamp_sec=t_sec, frame_id=fid)

        if not targets:
            return [], PoseEstimateResult(
                timestamp_sec=t_sec,
                frame_id=fid,
                is_valid=False,
                failure_reason="No fiducial marker detected in frame",
            ), None

        # Step 2: Select primary landing target (highest confidence or largest area)
        primary_target = targets[0]

        # Step 3: Corner Geometric Validation
        corners_np = np.array(primary_target.corners, dtype=np.float64)
        is_valid_geo, err_reason = self.validator.validate(corners_np)

        if not is_valid_geo:
            logger.warning("Landing target %d corners failed validation: %s", primary_target.target_id, err_reason)
            return targets, PoseEstimateResult(
                timestamp_sec=t_sec,
                frame_id=fid,
                target_id=primary_target.target_id,
                target=primary_target,
                is_valid=False,
                failure_reason=f"Degenerate corner geometry: {err_reason}",
            ), None

        # Step 4: Solve 6-DoF Pose via PnP
        obj_pts = self.geometry.get_object_points()
        pose_result = self.pnp_solver.solve(
            object_points_3d=obj_pts,
            image_points_2d=corners_np,
            camera_model=self.camera_model,
            target_id=primary_target.target_id,
            frame_id=fid,
            timestamp_sec=t_sec,
        )
        pose_result.target = primary_target

        # Step 5: Construct Unified LandingPad Representation
        landing_pad = None
        if pose_result.is_valid and pose_result.pose is not None:
            landing_pad = LandingPad(
                pad_id=primary_target.target_id,
                target_type="fiducial",
                marker_id=primary_target.marker_id,
                marker_size_m=self.geometry.marker_size_m,
                pose=pose_result.pose,
                corners_2d=primary_target.corners,
                confidence=primary_target.confidence,
                is_trackable=True,
            )

        return targets, pose_result, landing_pad
