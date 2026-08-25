from typing import Optional, Tuple
import numpy as np


from skyvanta.core.types import ErrorState, FilterStatus, FrameId, NominalState
from skyvanta.spatial.transform import (
    quaternion_to_rotation_matrix,
    rotation_matrix_to_euler,
    rotation_matrix_to_quaternion,
)

# Standardized 15-State Error Vector Ordering
STATE_DIM = 15
INDEX_POS = slice(0, 3)     # delta_p: World position error (m)
INDEX_VEL = slice(3, 6)     # delta_v: World velocity error (m/s)
INDEX_ATT = slice(6, 9)     # delta_theta: Body attitude error vector (rad)
INDEX_BG = slice(9, 12)     # delta_bg: Gyroscope bias error (rad/s)
INDEX_BA = slice(12, 15)    # delta_ba: Accelerometer bias error (m/s²)


class ESEKFState:
    """Internal mathematical wrapper for 15-state ESEKF nominal state and error covariance."""

    def __init__(
        self,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation_matrix: Optional[np.ndarray] = None,
        gyro_bias: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        accel_bias: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        timestamp_sec: float = 0.0,
        covariance: Optional[np.ndarray] = None,
        status: FilterStatus = FilterStatus.UNINITIALIZED,
    ):
        self.timestamp_sec = float(timestamp_sec)
        self.p = np.array(position, dtype=np.float64).flatten()
        self.v = np.array(velocity, dtype=np.float64).flatten()
        self.R = np.eye(3, dtype=np.float64) if rotation_matrix is None else np.ascontiguousarray(rotation_matrix, dtype=np.float64).reshape(3, 3)
        self.b_g = np.array(gyro_bias, dtype=np.float64).flatten()
        self.b_a = np.array(accel_bias, dtype=np.float64).flatten()
        self.status = status

        if covariance is None:
            self.P = np.eye(STATE_DIM, dtype=np.float64)
        else:
            self.P = np.ascontiguousarray(covariance, dtype=np.float64).reshape(STATE_DIM, STATE_DIM)

    def to_nominal_state(self) -> NominalState:
        """Exports to Pydantic NominalState schema."""
        quat = rotation_matrix_to_quaternion(self.R)
        _, euler_deg = rotation_matrix_to_euler(self.R)

        return NominalState(
            timestamp_sec=self.timestamp_sec,
            position_world=(float(self.p[0]), float(self.p[1]), float(self.p[2])),
            velocity_world=(float(self.v[0]), float(self.v[1]), float(self.v[2])),
            rotation_matrix=self.R.tolist(),
            quaternion=quat,
            euler_deg=euler_deg,
            gyro_bias=(float(self.b_g[0]), float(self.b_g[1]), float(self.b_g[2])),
            accel_bias=(float(self.b_a[0]), float(self.b_a[1]), float(self.b_a[2])),
            frame_id=FrameId.WORLD,
            status=self.status,
        )
