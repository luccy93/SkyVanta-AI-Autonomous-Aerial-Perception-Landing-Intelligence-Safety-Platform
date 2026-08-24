"""Formal Special Euclidean Group SE(3) homogeneous spatial transformation abstraction."""

import math
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from skyvanta.core.exceptions import InvalidTransformError
from skyvanta.core.types import FrameId, Pose6D
from skyvanta.spatial.transform import (
    euler_to_rotation_matrix,
    quaternion_to_rotation_matrix,
    rotation_matrix_to_euler,
    rotation_matrix_to_quaternion,
    rotation_matrix_to_rvec,
    rvec_to_rotation_matrix,
)


class SE3Transform:
    """Rigid 3D transformation member of the Special Euclidean Group SE(3).

    Represents the homogeneous transformation matrix:
        T_target_source = [ R  t ]
                          [ 0  1 ]
    where:
        - R in SO(3) is a 3x3 orthonormal rotation matrix (det(R) = +1, R^T R = I).
        - t in R^3 is a 3x1 translation vector in meters.
        - Transforms a 3D point p_source into p_target: p_target = R * p_source + t.
    """

    def __init__(
        self,
        source_frame: Union[FrameId, str],
        target_frame: Union[FrameId, str],
        rotation: Optional[np.ndarray] = None,
        translation: Optional[Union[np.ndarray, List[float], Tuple[float, float, float]]] = None,
        timestamp_sec: float = 0.0,
        is_static: bool = True,
        tolerance_orthonormal: float = 1e-3,
        tolerance_det: float = 1e-3,
    ):
        self.source_frame = FrameId(source_frame) if isinstance(source_frame, str) else source_frame
        self.target_frame = FrameId(target_frame) if isinstance(target_frame, str) else target_frame
        self.timestamp_sec = float(timestamp_sec)
        self.is_static = bool(is_static)

        # Default rotation: Identity
        if rotation is None:
            self._R = np.eye(3, dtype=np.float64)
        else:
            self._R = np.ascontiguousarray(rotation, dtype=np.float64).reshape(3, 3)

        # Default translation: Zeros
        if translation is None:
            self._t = np.zeros(3, dtype=np.float64)
        else:
            self._t = np.ascontiguousarray(translation, dtype=np.float64).flatten()

        self.validate(tolerance_orthonormal=tolerance_orthonormal, tolerance_det=tolerance_det)

    @property
    def rotation_matrix(self) -> np.ndarray:
        """Returns (3, 3) rotation matrix R in SO(3)."""
        return self._R.copy()

    @property
    def translation(self) -> np.ndarray:
        """Returns (3,) translation vector in meters."""
        return self._t.copy()

    def validate(self, tolerance_orthonormal: float = 1e-3, tolerance_det: float = 1e-3) -> None:
        """Validates numerical integrity and SO(3) mathematical constraints."""
        if self._R.shape != (3, 3):
            raise InvalidTransformError(f"Rotation matrix must be shape (3, 3), got {self._R.shape}")

        if self._t.shape != (3,):
            raise InvalidTransformError(f"Translation vector must be shape (3,), got {self._t.shape}")

        if not np.all(np.isfinite(self._R)) or not np.all(np.isfinite(self._t)):
            raise InvalidTransformError("Transform contains non-finite (NaN or Inf) values")

        # Check Orthonormality: R^T * R ≈ I
        rt_r = self._R.T @ self._R
        ortho_diff = np.max(np.abs(rt_r - np.eye(3)))
        if ortho_diff > tolerance_orthonormal:
            raise InvalidTransformError(
                f"Rotation matrix violates SO(3) orthonormality (max error {ortho_diff:.6f} > {tolerance_orthonormal})"
            )

        # Check Determinant: det(R) ≈ +1 (Proper rotation, not reflection)
        det = float(np.linalg.det(self._R))
        if abs(det - 1.0) > tolerance_det:
            raise InvalidTransformError(
                f"Rotation matrix determinant det(R)={det:.6f} violates SO(3) proper rotation (|det - 1| > {tolerance_det})"
            )

    @classmethod
    def identity(cls, frame: Union[FrameId, str]) -> "SE3Transform":
        """Creates an identity SE(3) transform for a frame."""
        fid = FrameId(frame) if isinstance(frame, str) else frame
        return cls(source_frame=fid, target_frame=fid, rotation=np.eye(3), translation=np.zeros(3), is_static=True)

    @classmethod
    def from_matrix(
        cls,
        matrix_4x4: np.ndarray,
        source_frame: Union[FrameId, str],
        target_frame: Union[FrameId, str],
        timestamp_sec: float = 0.0,
        is_static: bool = True,
    ) -> "SE3Transform":
        """Constructs an SE3Transform from a 4x4 homogeneous matrix."""
        mat = np.ascontiguousarray(matrix_4x4, dtype=np.float64)
        if mat.shape != (4, 4):
            raise InvalidTransformError(f"Homogeneous matrix must be shape (4, 4), got {mat.shape}")

        R = mat[:3, :3]
        t = mat[:3, 3]
        bottom = mat[3, :]

        if not np.allclose(bottom, [0.0, 0.0, 0.0, 1.0], atol=1e-5):
            raise InvalidTransformError(f"Bottom row of homogeneous matrix must be [0, 0, 0, 1], got {bottom}")

        return cls(
            source_frame=source_frame,
            target_frame=target_frame,
            rotation=R,
            translation=t,
            timestamp_sec=timestamp_sec,
            is_static=is_static,
        )

    @classmethod
    def from_pose6d(
        cls,
        pose: Pose6D,
        source_frame: Union[FrameId, str],
        target_frame: Union[FrameId, str],
        is_static: bool = False,
    ) -> "SE3Transform":
        """Constructs an SE3Transform from a Pose6D model."""
        R = np.array(pose.rotation_matrix, dtype=np.float64)
        t = np.array([pose.x, pose.y, pose.z], dtype=np.float64)
        return cls(
            source_frame=source_frame,
            target_frame=target_frame,
            rotation=R,
            translation=t,
            timestamp_sec=pose.timestamp_sec,
            is_static=is_static,
        )

    @classmethod
    def from_euler(
        cls,
        source_frame: Union[FrameId, str],
        target_frame: Union[FrameId, str],
        translation: Tuple[float, float, float],
        euler_deg: Tuple[float, float, float],
        timestamp_sec: float = 0.0,
        is_static: bool = True,
    ) -> "SE3Transform":
        """Constructs an SE3Transform from Euler angles in degrees (roll, pitch, yaw) and translation."""
        roll_rad, pitch_rad, yaw_rad = (math.radians(a) for a in euler_deg)
        R = euler_to_rotation_matrix(roll_rad, pitch_rad, yaw_rad)
        return cls(
            source_frame=source_frame,
            target_frame=target_frame,
            rotation=R,
            translation=translation,
            timestamp_sec=timestamp_sec,
            is_static=is_static,
        )

    def to_matrix(self) -> np.ndarray:
        """Returns the 4x4 homogeneous transformation matrix."""
        mat = np.eye(4, dtype=np.float64)
        mat[:3, :3] = self._R
        mat[:3, 3] = self._t
        return mat

    def to_pose6d(
        self,
        target_id: int = 0,
        frame_id: int = 0,
        reprojection_error_rms: float = 0.0,
        pose_quality: float = 1.0,
        is_valid: bool = True,
        solver_method: str = "SE3_COMPOSED",
    ) -> Pose6D:
        """Exports the transform as a standard Pose6D model."""
        quat = rotation_matrix_to_quaternion(self._R)
        rvec = rotation_matrix_to_rvec(self._R)
        euler_rad, euler_deg = rotation_matrix_to_euler(self._R)
        tx, ty, tz = float(self._t[0]), float(self._t[1]), float(self._t[2])
        range_m = float(math.sqrt(tx * tx + ty * ty + tz * tz))

        return Pose6D(
            x=tx,
            y=ty,
            z=tz,
            rotation_matrix=self._R.tolist(),
            rvec=(float(rvec[0]), float(rvec[1]), float(rvec[2])),
            quaternion=quat,
            euler_deg=euler_deg,
            euler_rad=euler_rad,
            range_m=range_m,
            reprojection_error_rms=reprojection_error_rms,
            reprojection_error_max=reprojection_error_rms,
            pose_quality=pose_quality,
            is_valid=is_valid,
            timestamp_sec=self.timestamp_sec,
            frame_id=frame_id,
            target_id=target_id,
            solver_method=solver_method,
        )

    def inverse(self) -> "SE3Transform":
        """Computes the exact inverse transform T_source_target = T_target_source^(-1).

        Mathematical formulation:
            T^(-1) = [ R^T  -R^T * t ]
                     [  0        1   ]
        """
        R_inv = self._R.T
        t_inv = -R_inv @ self._t
        return SE3Transform(
            source_frame=self.target_frame,
            target_frame=self.source_frame,
            rotation=R_inv,
            translation=t_inv,
            timestamp_sec=self.timestamp_sec,
            is_static=self.is_static,
        )

    def compose(self, other: "SE3Transform") -> "SE3Transform":
        """Composes two SE(3) transforms: T_A_C = T_A_B * T_B_C.

        Args:
            other: SE3Transform T_B_C where other.target_frame must equal self.source_frame
                   or other.source_frame equals self.target_frame.

        Returns:
            Composed SE3Transform.
        """
        # Standard composition: T_target_intermediate * T_intermediate_source
        if self.source_frame != other.target_frame:
            raise InvalidTransformError(
                f"Cannot compose transforms with mismatched intermediate frames: "
                f"T_{self.target_frame}_{self.source_frame} * T_{other.target_frame}_{other.source_frame}"
            )

        R_composed = self._R @ other._R
        t_composed = self._R @ other._t + self._t
        timestamp = max(self.timestamp_sec, other.timestamp_sec)
        is_static = self.is_static and other.is_static

        return SE3Transform(
            source_frame=other.source_frame,
            target_frame=self.target_frame,
            rotation=R_composed,
            translation=t_composed,
            timestamp_sec=timestamp,
            is_static=is_static,
        )

    def __matmul__(self, other: "SE3Transform") -> "SE3Transform":
        """Allows pythonic matrix multiplication operator @ for transform composition."""
        return self.compose(other)

    def transform_point(self, point_3d: Union[Tuple[float, float, float], List[float], np.ndarray]) -> np.ndarray:
        """Transforms a single 3D point p_source into p_target: p_target = R * p_source + t."""
        p = np.ascontiguousarray(point_3d, dtype=np.float64).flatten()
        if p.shape != (3,):
            raise InvalidTransformError(f"3D point must be shape (3,), got {p.shape}")
        if not np.all(np.isfinite(p)):
            raise InvalidTransformError("3D point contains non-finite values")
        return self._R @ p + self._t

    def transform_points(self, points_3d: np.ndarray) -> np.ndarray:
        """Transforms an array of 3D points (N, 3) from source frame to target frame."""
        pts = np.ascontiguousarray(points_3d, dtype=np.float64)
        if len(pts.shape) != 2 or pts.shape[1] != 3:
            raise InvalidTransformError(f"Points array must be shape (N, 3), got {pts.shape}")
        if not np.all(np.isfinite(pts)):
            raise InvalidTransformError("Points array contains non-finite values")

        # P_target = P_source * R^T + t^T
        return pts @ self._R.T + self._t

    def transform_pose(self, pose: Pose6D, new_target_frame: Optional[FrameId] = None) -> Pose6D:
        """Transforms a 6-DoF pose (both translation and rotation) into the new target frame."""
        R_pose = np.array(pose.rotation_matrix, dtype=np.float64)
        t_pose = np.array([pose.x, pose.y, pose.z], dtype=np.float64)

        R_transformed = self._R @ R_pose
        t_transformed = self._R @ t_pose + self._t

        tx, ty, tz = float(t_transformed[0]), float(t_transformed[1]), float(t_transformed[2])
        range_m = float(math.sqrt(tx * tx + ty * ty + tz * tz))
        quat = rotation_matrix_to_quaternion(R_transformed)
        rvec = rotation_matrix_to_rvec(R_transformed)
        euler_rad, euler_deg = rotation_matrix_to_euler(R_transformed)

        return Pose6D(
            x=tx,
            y=ty,
            z=tz,
            rotation_matrix=R_transformed.tolist(),
            rvec=(float(rvec[0]), float(rvec[1]), float(rvec[2])),
            quaternion=quat,
            euler_deg=euler_deg,
            euler_rad=euler_rad,
            range_m=range_m,
            reprojection_error_rms=pose.reprojection_error_rms,
            reprojection_error_max=pose.reprojection_error_max,
            pose_quality=pose.pose_quality,
            is_valid=pose.is_valid,
            timestamp_sec=pose.timestamp_sec,
            frame_id=pose.frame_id,
            target_id=pose.target_id,
            solver_method=f"{pose.solver_method}_TRANSFORMED",
        )
