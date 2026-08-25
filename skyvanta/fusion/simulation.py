import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


from skyvanta.core.types import FrameId, IMUMeasurement, VisualPoseMeasurement
from skyvanta.spatial.transform import euler_to_rotation_matrix, rotation_matrix_to_quaternion


class SyntheticTrajectory:
    """Generates ground truth kinematics trajectories for simulation."""

    @staticmethod
    def stationary(
        duration_sec: float = 5.0,
        dt_sec: float = 0.01,
        position: Tuple[float, float, float] = (0.0, 0.0, -10.0),
        euler_deg: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> List[Dict[str, Any]]:
        """Generates stationary hovering trajectory."""
        steps = int(duration_sec / dt_sec)
        R = euler_to_rotation_matrix(math.radians(euler_deg[0]), math.radians(euler_deg[1]), math.radians(euler_deg[2]))
        trajectory = []

        for i in range(steps):
            t = i * dt_sec
            trajectory.append({
                "time": t,
                "position": np.array(position, dtype=np.float64),
                "velocity": np.zeros(3, dtype=np.float64),
                "acceleration": np.zeros(3, dtype=np.float64),
                "rotation": R.copy(),
                "angular_velocity": np.zeros(3, dtype=np.float64),
            })
        return trajectory

    @staticmethod
    def constant_velocity(
        duration_sec: float = 5.0,
        dt_sec: float = 0.01,
        initial_pos: Tuple[float, float, float] = (0.0, 0.0, -10.0),
        velocity: Tuple[float, float, float] = (1.0, -0.5, 0.2),
        euler_deg: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> List[Dict[str, Any]]:
        """Generates straight-line constant velocity trajectory."""
        steps = int(duration_sec / dt_sec)
        R = euler_to_rotation_matrix(math.radians(euler_deg[0]), math.radians(euler_deg[1]), math.radians(euler_deg[2]))
        p0 = np.array(initial_pos, dtype=np.float64)
        v = np.array(velocity, dtype=np.float64)
        trajectory = []

        for i in range(steps):
            t = i * dt_sec
            p = p0 + v * t
            trajectory.append({
                "time": t,
                "position": p,
                "velocity": v.copy(),
                "acceleration": np.zeros(3, dtype=np.float64),
                "rotation": R.copy(),
                "angular_velocity": np.zeros(3, dtype=np.float64),
            })
        return trajectory


class SensorSimulator:
    """Generates synthetic IMU and visual pose measurements from ground-truth trajectories."""

    def __init__(
        self,
        gravity_m_s2: float = 9.80665,
        accel_bias: Tuple[float, float, float] = (0.02, -0.01, 0.03),
        gyro_bias: Tuple[float, float, float] = (0.005, -0.002, 0.001),
        accel_noise_std: float = 0.01,
        gyro_noise_std: float = 0.001,
        visual_noise_std_m: float = 0.02,
        visual_noise_std_rad: float = 0.01,
        random_seed: Optional[int] = 42,
    ):
        self.gravity_vec_world = np.array([0.0, 0.0, gravity_m_s2], dtype=np.float64)
        self.ba = np.array(accel_bias, dtype=np.float64)
        self.bg = np.array(gyro_bias, dtype=np.float64)
        self.sigma_a = accel_noise_std
        self.sigma_g = gyro_noise_std
        self.sigma_v_pos = visual_noise_std_m
        self.sigma_v_att = visual_noise_std_rad
        self.rng = np.random.default_rng(random_seed)

    def generate_imu(self, state: Dict[str, Any]) -> IMUMeasurement:
        """Generates an IMU sample with specific force reaction, true gravity, bias, and noise."""
        t = float(state["time"])
        R = state["rotation"]
        a_true = state["acceleration"]
        w_true = state["angular_velocity"]

        # Accelerometer measures specific force in body frame: a_m = R^T * (a_true - g_world) + ba + na
        specific_force_world = a_true - self.gravity_vec_world
        a_body = R.T @ specific_force_world + self.ba + self.rng.normal(0.0, self.sigma_a, size=3)

        # Gyroscope measures body angular velocity: w_m = w_true + bg + ng
        w_body = w_true + self.bg + self.rng.normal(0.0, self.sigma_g, size=3)

        return IMUMeasurement(
            timestamp_sec=max(0.001, t),
            angular_velocity_rad_s=(float(w_body[0]), float(w_body[1]), float(w_body[2])),
            linear_acceleration_m_s2=(float(a_body[0]), float(a_body[1]), float(a_body[2])),
            frame_id=FrameId.BODY,
        )

    def generate_visual_pose(
        self,
        state: Dict[str, Any],
        is_outlier: bool = False,
    ) -> VisualPoseMeasurement:
        """Generates a visual pose observation with Gaussian noise or optional outlier perturbation."""
        t = float(state["time"])
        p_true = state["position"]
        R_true = state["rotation"]

        noise_p = self.rng.normal(0.0, self.sigma_v_pos, size=3) if not is_outlier else np.array([5.0, -8.0, 10.0])
        p_meas = p_true + noise_p

        quat_true = rotation_matrix_to_quaternion(R_true)

        return VisualPoseMeasurement(
            timestamp_sec=max(0.001, t),
            position_m=(float(p_meas[0]), float(p_meas[1]), float(p_meas[2])),
            rotation_matrix=R_true.tolist(),
            quaternion=quat_true,
            frame_id=FrameId.WORLD,
            quality=1.0 if not is_outlier else 0.1,
            source="synthetic_sim",
            target_id=1,
        )
