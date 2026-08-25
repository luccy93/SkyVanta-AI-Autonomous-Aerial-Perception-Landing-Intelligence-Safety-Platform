"""IMU state propagation, error-state transition Jacobians, and covariance prediction."""

from typing import Optional, Tuple
import numpy as np

from skyvanta.core.config import IMUNoiseConfig
from skyvanta.fusion.imu import GravityModel
from skyvanta.fusion.so3 import skew_symmetric, so3_exp
from skyvanta.fusion.state import ESEKFState, STATE_DIM


class StatePropagator:
    """Propagates the 15-state nominal kinematics and discrete error covariance forward in time."""

    def __init__(
        self,
        noise_config: Optional[IMUNoiseConfig] = None,
        gravity_model: Optional[GravityModel] = None,
    ):
        self.noise_cfg = noise_config or IMUNoiseConfig()
        self.gravity = gravity_model or GravityModel()

    def build_discrete_noise_matrix(self, dt: float) -> np.ndarray:
        """Constructs the discrete 15x15 process noise covariance matrix Q_k."""
        Q = np.zeros((STATE_DIM, STATE_DIM), dtype=np.float64)

        var_a = self.noise_cfg.accel_noise_density ** 2
        var_g = self.noise_cfg.gyro_noise_density ** 2
        var_ba = self.noise_cfg.accel_bias_random_walk ** 2
        var_bg = self.noise_cfg.gyro_bias_random_walk ** 2

        # Position block (0..3)
        Q[0:3, 0:3] = np.eye(3) * (var_a * (dt ** 3) / 3.0)
        Q[0:3, 3:6] = np.eye(3) * (var_a * (dt ** 2) / 2.0)
        Q[3:6, 0:3] = Q[0:3, 3:6]

        # Velocity block (3..6)
        Q[3:6, 3:6] = np.eye(3) * (var_a * dt)

        # Attitude block (6..9)
        Q[6:9, 6:9] = np.eye(3) * (var_g * dt)

        # Gyro bias random walk (9..12)
        Q[9:12, 9:12] = np.eye(3) * (var_bg * dt)

        # Accel bias random walk (12..15)
        Q[12:15, 12:15] = np.eye(3) * (var_ba * dt)

        return Q

    def compute_transition_matrix(
        self,
        R: np.ndarray,
        unbiased_accel: np.ndarray,
        unbiased_gyro: np.ndarray,
        dt: float,
    ) -> np.ndarray:
        """Computes the 15x15 discrete error-state transition matrix Phi_k ≈ I + F_c * dt + 0.5 * (F_c * dt)^2."""
        Fc = np.zeros((STATE_DIM, STATE_DIM), dtype=np.float64)

        # dp_dot = dv
        Fc[0:3, 3:6] = np.eye(3)

        # dv_dot = -R * [a_unbiased]_x * dtheta - R * dba
        Fc[3:6, 6:9] = -R @ skew_symmetric(unbiased_accel)
        Fc[3:6, 12:15] = -R

        # dtheta_dot = -[w_unbiased]_x * dtheta - dbg
        Fc[6:9, 6:9] = -skew_symmetric(unbiased_gyro)
        Fc[6:9, 9:12] = -np.eye(3)

        # Second-order Taylor series for discrete state transition matrix
        F_dt = Fc * dt
        Phi = np.eye(STATE_DIM, dtype=np.float64) + F_dt + 0.5 * (F_dt @ F_dt)
        return Phi

    def propagate(
        self,
        state: ESEKFState,
        angular_velocity: np.ndarray,
        linear_acceleration: np.ndarray,
        dt: float,
        timestamp_sec: float,
    ) -> ESEKFState:
        """Executes full nominal state and error covariance propagation over time step dt."""
        w_m = np.ascontiguousarray(angular_velocity, dtype=np.float64).flatten()
        a_m = np.ascontiguousarray(linear_acceleration, dtype=np.float64).flatten()

        # 1. Compensate estimated biases
        unbiased_gyro = w_m - state.b_g
        unbiased_accel = a_m - state.b_a

        # 2. Gravity vector in World frame
        g_world = self.gravity.gravity_vector

        # 3. Propagate Nominal Kinematics
        accel_world = state.R @ unbiased_accel + g_world
        p_next = state.p + state.v * dt + 0.5 * accel_world * (dt ** 2)
        v_next = state.v + accel_world * dt
        R_next = state.R @ so3_exp(unbiased_gyro * dt)

        # Biases follow random-walk (constant expectation)
        bg_next = state.b_g.copy()
        ba_next = state.b_a.copy()

        # 4. Propagate Error Covariance P
        Phi = self.compute_transition_matrix(state.R, unbiased_accel, unbiased_gyro, dt)
        Q = self.build_discrete_noise_matrix(dt)
        P_next = Phi @ state.P @ Phi.T + Q

        # Numerical symmetrization
        P_next = 0.5 * (P_next + P_next.T)

        return ESEKFState(
            position=(float(p_next[0]), float(p_next[1]), float(p_next[2])),
            velocity=(float(v_next[0]), float(v_next[1]), float(v_next[2])),
            rotation_matrix=R_next,
            gyro_bias=(float(bg_next[0]), float(bg_next[1]), float(bg_next[2])),
            accel_bias=(float(ba_next[0]), float(ba_next[1]), float(ba_next[2])),
            timestamp_sec=timestamp_sec,
            covariance=P_next,
            status=state.status,
        )
