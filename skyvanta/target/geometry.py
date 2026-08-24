"""Physical 3D target geometry definitions for planar fiducial markers."""

import numpy as np
from skyvanta.core.exceptions import GeometryError


class TargetGeometry:
    """Defines the 3D metric coordinate model for a planar square fiducial marker."""

    def __init__(self, marker_size_m: float):
        if marker_size_m <= 0.0:
            raise GeometryError(f"Marker size must be strictly positive (received {marker_size_m}m)")

        self.marker_size_m = float(marker_size_m)
        s = self.marker_size_m / 2.0

        # Standard planar square coordinate definition:
        # Origin (0, 0, 0) at marker geometric center.
        # +X is right, +Y is down, +Z is normal into the marker.
        # Order: Top-Left (0), Top-Right (1), Bottom-Right (2), Bottom-Left (3)
        self.object_points_3d = np.array([
            [-s, -s, 0.0],
            [+s, -s, 0.0],
            [+s, +s, 0.0],
            [-s, +s, 0.0],
        ], dtype=np.float64)

    def get_object_points(self) -> np.ndarray:
        """Returns (4, 3) numpy array of 3D object points in meters."""
        return self.object_points_3d.copy()
