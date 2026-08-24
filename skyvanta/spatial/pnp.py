"""Perspective-n-Point (PnP) 6-DoF spatial pose solver with reprojection error validation."""

import math
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

from skyvanta.core.config import PnPConfig, PoseQualityConfig
from skyvanta.core.logging import get_logger
from skyvanta.core.types import Pose6D, PoseEstimateResult
from skyvanta.spatial.camera import CameraModel
from skyvanta.spatial.transform import (
    rotation_matrix_to_euler,
    rotation_matrix_to_quaternion,
    rotation_matrix_to_rvec,
    rvec_to_rotation_matrix,
)

logger = get_logger("skyvanta.spatial.pnp")


class PnPPoseSolver:
    """Estimates camera-relative 6-DoF spatial pose from 3D-2D point correspondences."""

    def __init__(
        self,
        pnp_config: Optional[PnPConfig] = None,
        quality_config: Optional[PoseQualityConfig] = None,
    ):
        self.pnp_config = pnp_config or PnPConfig()
        self.quality_config = quality_config or PoseQualityConfig()

        # Map solver string to OpenCV flag
        solver_map = {
            "IPPE": cv2.SOLVEPNP_IPPE,
            "ITERATIVE": cv2.SOLVEPNP_ITERATIVE,
            "EPNP": cv2.SOLVEPNP_EPNP,
            "P3P": cv2.SOLVEPNP_P3P,
            "SQPNP": cv2.SOLVEPNP_SQPNP if hasattr(cv2, "SOLVEPNP_SQPNP") else cv2.SOLVEPNP_ITERATIVE,
            "RANSAC": -1,  # Uses cv2.solvePnPRansac
        }
        self.solver_flag = solver_map.get(self.pnp_config.solver.upper(), cv2.SOLVEPNP_IPPE)

    def solve(
        self,
        object_points_3d: np.ndarray,
        image_points_2d: np.ndarray,
        camera_model: CameraModel,
        target_id: int = 0,
        frame_id: int = 0,
        timestamp_sec: float = 0.0,
    ) -> PoseEstimateResult:
        """Solves 6-DoF pose of target in camera optical frame.

        Args:
            object_points_3d: (N, 3) array of 3D object coordinates in target frame (meters).
            image_points_2d: (N, 2) array of observed 2D pixel coordinates.
            camera_model: Calibrated CameraModel instance.
            target_id: Associated target ID.
            frame_id: Video frame sequence index.
            timestamp_sec: Timestamp in seconds.

        Returns:
            PoseEstimateResult containing validated Pose6D or failure diagnosis.
        """
        obj_pts = np.ascontiguousarray(object_points_3d, dtype=np.float64).reshape(-1, 3)
        img_pts = np.ascontiguousarray(image_points_2d, dtype=np.float64).reshape(-1, 2)

        if len(obj_pts) < 4 or len(img_pts) < 4:
            return PoseEstimateResult(
                timestamp_sec=timestamp_sec,
                frame_id=frame_id,
                target_id=target_id,
                is_valid=False,
                failure_reason="Insufficient point correspondences (minimum 4 points required for planar PnP)",
            )

        if not np.all(np.isfinite(img_pts)) or not np.all(np.isfinite(obj_pts)):
            return PoseEstimateResult(
                timestamp_sec=timestamp_sec,
                frame_id=frame_id,
                target_id=target_id,
                is_valid=False,
                failure_reason="Non-finite values detected in image or object points",
            )

        try:
            if self.solver_flag == -1:  # RANSAC
                success, rvec, tvec, inliers = cv2.solvePnPRansac(
                    obj_pts,
                    img_pts,
                    camera_model.matrix_k,
                    camera_model.dist_coeffs,
                    reprojectionError=self.pnp_config.max_reprojection_error_px,
                )
            elif self.solver_flag == cv2.SOLVEPNP_IPPE and len(obj_pts) == 4:
                # IPPE returns both ambiguous planar poses if solvePnPGeneric is used, or best pose with solvePnP
                success, rvec, tvec = cv2.solvePnP(
                    obj_pts,
                    img_pts,
                    camera_model.matrix_k,
                    camera_model.dist_coeffs,
                    flags=cv2.SOLVEPNP_IPPE,
                )
            else:
                success, rvec, tvec = cv2.solvePnP(
                    obj_pts,
                    img_pts,
                    camera_model.matrix_k,
                    camera_model.dist_coeffs,
                    flags=self.solver_flag if self.solver_flag != -1 else cv2.SOLVEPNP_ITERATIVE,
                )

            if not success or rvec is None or tvec is None:
                return PoseEstimateResult(
                    timestamp_sec=timestamp_sec,
                    frame_id=frame_id,
                    target_id=target_id,
                    is_valid=False,
                    failure_reason="OpenCV solvePnP returned failure / no solution found",
                )

            rvec = rvec.flatten()
            tvec = tvec.flatten()

            tx, ty, tz = float(tvec[0]), float(tvec[1]), float(tvec[2])

            if not (math.isfinite(tx) and math.isfinite(ty) and math.isfinite(tz)):
                return PoseEstimateResult(
                    timestamp_sec=timestamp_sec,
                    frame_id=frame_id,
                    target_id=target_id,
                    is_valid=False,
                    failure_reason=f"Non-finite translation solved: t=[{tx}, {ty}, {tz}]",
                )

            # Check optical depth validity (Z must be positive and in bounds)
            if tz <= self.pnp_config.min_depth_m:
                return PoseEstimateResult(
                    timestamp_sec=timestamp_sec,
                    frame_id=frame_id,
                    target_id=target_id,
                    is_valid=False,
                    failure_reason=f"Target depth z={tz:.3f}m is behind or too close to camera (< {self.pnp_config.min_depth_m}m)",
                )
            if tz > self.pnp_config.max_depth_m:
                return PoseEstimateResult(
                    timestamp_sec=timestamp_sec,
                    frame_id=frame_id,
                    target_id=target_id,
                    is_valid=False,
                    failure_reason=f"Target depth z={tz:.3f}m exceeds maximum tracking range ({self.pnp_config.max_depth_m}m)",
                )

            # Calculate Reprojection Error
            projected = camera_model.project_points(obj_pts, rvec, tvec)
            errors = np.linalg.norm(img_pts - projected, axis=1)
            rms_error = float(np.sqrt(np.mean(errors ** 2)))
            max_error = float(np.max(errors))

            if rms_error > self.pnp_config.max_reprojection_error_px:
                return PoseEstimateResult(
                    timestamp_sec=timestamp_sec,
                    frame_id=frame_id,
                    target_id=target_id,
                    reprojection_error_rms=rms_error,
                    is_valid=False,
                    failure_reason=f"Reprojection RMS error {rms_error:.2f}px exceeds gate ({self.pnp_config.max_reprojection_error_px}px)",
                )

            # Compute Rotation Representations
            R_mat = rvec_to_rotation_matrix(rvec)
            quat = rotation_matrix_to_quaternion(R_mat)
            euler_rad, euler_deg = rotation_matrix_to_euler(R_mat)
            range_m = float(math.sqrt(tx * tx + ty * ty + tz * tz))

            # Quality Assessment
            reproj_penalty = max(0.0, 1.0 - (rms_error / self.quality_config.max_reproj_error_for_zero_quality))
            pose_quality = float(max(0.0, min(1.0, reproj_penalty)))

            pose6d = Pose6D(
                x=tx,
                y=ty,
                z=tz,
                rotation_matrix=R_mat.tolist(),
                rvec=(float(rvec[0]), float(rvec[1]), float(rvec[2])),
                quaternion=quat,
                euler_deg=euler_deg,
                euler_rad=euler_rad,
                range_m=range_m,
                reprojection_error_rms=rms_error,
                reprojection_error_max=max_error,
                pose_quality=pose_quality,
                is_valid=True,
                timestamp_sec=timestamp_sec,
                frame_id=frame_id,
                target_id=target_id,
                solver_method=self.pnp_config.solver,
            )

            return PoseEstimateResult(
                timestamp_sec=timestamp_sec,
                frame_id=frame_id,
                target_id=target_id,
                pose=pose6d,
                reprojection_error_rms=rms_error,
                pose_quality=pose_quality,
                is_valid=True,
                failure_reason=None,
                solver_metadata={
                    "solver_method": self.pnp_config.solver,
                    "rms_error_px": rms_error,
                    "max_error_px": max_error,
                },
            )

        except Exception as e:
            logger.error("PnP solver exception for target %d: %s", target_id, e)
            return PoseEstimateResult(
                timestamp_sec=timestamp_sec,
                frame_id=frame_id,
                target_id=target_id,
                is_valid=False,
                failure_reason=f"PnP solver exception: {e}",
            )
