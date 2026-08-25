"""Simulated landing target platform model."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from skyvanta.simulation.dropout import OcclusionModel
from skyvanta.spatial.transform import euler_to_rotation_matrix
from skyvanta.target.geometry import TargetGeometry


class SimulatedLandingTarget:
    """Represents a fixed or moving ground/marine landing target platform."""

    def __init__(
        self,
        marker_size_m: float = 0.8,
        initial_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        velocity_mps: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        initial_euler_deg: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        angular_rate_deg_s: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        occlusion_model: Optional[OcclusionModel] = None,
        target_id: int = 1,
    ):
        self.geometry = TargetGeometry(marker_size_m=marker_size_m)
        self.initial_position = np.array(initial_position, dtype=np.float64)
        self.velocity = np.array(velocity_mps, dtype=np.float64)
        self.initial_euler_deg = np.array(initial_euler_deg, dtype=np.float64)
        self.angular_rate_deg_s = np.array(angular_rate_deg_s, dtype=np.float64)
        self.occlusion_model = occlusion_model or OcclusionModel()
        self.target_id = int(target_id)

    def get_position_at(self, timestamp_sec: float) -> np.ndarray:
        """Returns the 3D position [x, y, z] of the target center in World frame at timestamp_sec."""
        return self.initial_position + self.velocity * timestamp_sec

    def get_orientation_at(self, timestamp_sec: float) -> np.ndarray:
        """Returns the 3x3 rotation matrix R_WP in World frame at timestamp_sec."""
        import math
        euler = self.initial_euler_deg + self.angular_rate_deg_s * timestamp_sec
        return euler_to_rotation_matrix(
            math.radians(euler[0]), math.radians(euler[1]), math.radians(euler[2])
        )

    def get_3d_corners_world(self, timestamp_sec: float) -> np.ndarray:
        """Computes the 4 corners of the landing pad in World frame coordinates (4, 3)."""
        pos = self.get_position_at(timestamp_sec)
        rot = self.get_orientation_at(timestamp_sec)
        local_corners = self.geometry.get_object_points()  # (4, 3) with z=0
        # Transform local target points to world frame: p_W = R_WP * p_P + t_W
        return (rot @ local_corners.T).T + pos

    def is_visible(self, timestamp_sec: float) -> bool:
        """Checks whether the landing target is currently visible (unoccluded)."""
        return not self.occlusion_model.is_occluded(timestamp_sec)

    def get_state_dict(self, timestamp_sec: float) -> Dict[str, Any]:
        """Returns a serializable state dictionary."""
        pos = self.get_position_at(timestamp_sec)
        return {
            "target_id": self.target_id,
            "position_world": [float(x) for x in pos],
            "velocity_mps": [float(x) for x in self.velocity],
            "is_visible": self.is_visible(timestamp_sec),
            "marker_size_m": self.geometry.marker_size_m,
        }
