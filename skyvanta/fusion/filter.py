"""15-State Error-State Extended Kalman Filter (ESEKF) core estimation engine."""

import math
import time
from typing import Optional, Tuple
import numpy as np

from skyvanta.core.config import ESEKFConfig
from skyvanta.core.exceptions import InitializationError, NumericalDivergenceError
from skyvanta.core.logging import get_logger
from skyvanta.core.types import (
    ESEKFDiagnostics,
    ESEKFStateResult,
    FilterStatus,
    IMUMeasurement,
    NominalState,
    VisualPoseMeasurement,
)
from skyvanta.fusion.imu import GravityModel, IMUPreprocessor
from skyvanta.fusion.propagation import StatePropagator
from skyvanta.fusion.state import ESEKFState, STATE_DIM
from skyvanta.fusion.update import KalmanUpdater

logger = get_logger("skyvanta.fusion.esekf")


class ErrorStateExtendedKalmanFilter:
    """15-State Error-State Extended Kalman Filter for real-time IMU and visual sensor fusion."""

    def __init__(self, config: Optional[ESEKFConfig] = None):
        self.config = config or ESEKFConfig()
        self.gravity_model = GravityModel(self.config.gravity)
        self.imu_preprocessor = IMUPreprocessor(
            min_dt_sec=self.config.min_dt_sec,
            max_dt_sec=self.config.max_dt_sec,
        )
        self.propagator = StatePropagator(self.config.imu_noise, self.gravity_model)
        self.updater = KalmanUpdater(self.config)

        # Filter state & diagnostics
        self._state = self._create_default_state()
        self._diagnostics = ESEKFDiagnostics()

    def _create_default_state(self) -> ESEKFState:
        """Initializes uninitialized prior state with configured initial variances."""
        P_init = np.eye(STATE_DIM, dtype=np.float64)
        P_init[0:3, 0:3] = np.eye(3) * self.config.initial_pos_cov
        P_init[3:6, 3:6] = np.eye(3) * self.config.initial_vel_cov
        P_init[6:9, 6:9] = np.eye(3) * self.config.initial_att_cov
        P_init[9:12, 9:12] = np.eye(3) * self.config.initial_bg_cov
        P_init[12:15, 12:15] = np.eye(3) * self.config.initial_ba_cov

        return ESEKFState(covariance=P_init, status=FilterStatus.UNINITIALIZED)

    def initialize(
        self,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation_matrix: Optional[np.ndarray] = None,
        gyro_bias: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        accel_bias: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        timestamp_sec: float = 0.0,
        initial_covariance: Optional[np.ndarray] = None,
    ) -> None:
        """Explicitly initializes the nominal state and error covariance."""
        R = np.eye(3, dtype=np.float64) if rotation_matrix is None else np.array(rotation_matrix, dtype=np.float64)

        if not np.all(np.isfinite(position)) or not np.all(np.isfinite(velocity)):
            raise InitializationError("Non-finite initial position or velocity supplied")

        P = initial_covariance if initial_covariance is not None else self._state.P

        self._state = ESEKFState(
            position=position,
            velocity=velocity,
            rotation_matrix=R,
            gyro_bias=gyro_bias,
            accel_bias=accel_bias,
            timestamp_sec=timestamp_sec,
            covariance=P,
            status=FilterStatus.INITIALIZED,
        )
        self.imu_preprocessor.reset()
        logger.info("ESEKF successfully initialized at timestamp %.3fs", timestamp_sec)

    def propagate(self, measurement: IMUMeasurement) -> NominalState:
        """Propagates state estimate and error covariance using high-rate IMU measurement."""
        t_start = time.perf_counter()

        dt = self.imu_preprocessor.validate_and_compute_dt(measurement)

        w = np.array(measurement.angular_velocity_rad_s, dtype=np.float64)
        a = np.array(measurement.linear_acceleration_m_s2, dtype=np.float64)

        # Propagate nominal kinematics & error covariance
        self._state = self.propagator.propagate(
            state=self._state,
            angular_velocity=w,
            linear_acceleration=a,
            dt=dt,
            timestamp_sec=measurement.timestamp_sec,
        )

        # Update diagnostics
        dt_ms = (time.perf_counter() - t_start) * 1000.0
        self._diagnostics.propagation_count += 1
        self._diagnostics.processing_latency_ms = dt_ms
        self._update_uncertainty_metrics()

        return self._state.to_nominal_state()

    def update_visual(self, measurement: VisualPoseMeasurement) -> Tuple[NominalState, bool, Optional[str]]:
        """Updates state estimate using discrete 6-DoF visual pose observation."""
        t_start = time.perf_counter()

        updated_state, nis, accepted, reason = self.updater.update(self._state, measurement)

        self._diagnostics.last_nis = nis
        if accepted:
            self._state = updated_state
            self._diagnostics.visual_update_count += 1
            self._diagnostics.last_rejection_reason = None
            if self._state.status == FilterStatus.UNINITIALIZED:
                self._state.status = FilterStatus.INITIALIZED
        else:
            self._diagnostics.rejected_measurement_count += 1
            self._diagnostics.last_rejection_reason = reason
            logger.warning("Visual measurement update rejected: %s", reason)

        dt_ms = (time.perf_counter() - t_start) * 1000.0
        self._diagnostics.processing_latency_ms = dt_ms
        self._update_uncertainty_metrics()

        return self._state.to_nominal_state(), accepted, reason

    def _update_uncertainty_metrics(self) -> None:
        """Calculates 3-sigma uncertainty metrics from error covariance P."""
        diag = np.diag(self._state.P)
        if np.any(diag < 0) or not np.all(np.isfinite(diag)):
            raise NumericalDivergenceError("Covariance diagonal contains negative or non-finite variances")

        self._diagnostics.covariance_trace = float(np.trace(self._state.P))
        # 3-sigma position uncertainty
        self._diagnostics.position_uncertainty_m = float(3.0 * math.sqrt(max(0.0, np.sum(diag[0:3]))))
        # 3-sigma velocity uncertainty
        self._diagnostics.velocity_uncertainty_m_s = float(3.0 * math.sqrt(max(0.0, np.sum(diag[3:6]))))
        # 3-sigma attitude uncertainty in degrees
        self._diagnostics.orientation_uncertainty_deg = float(math.degrees(3.0 * math.sqrt(max(0.0, np.sum(diag[6:9])))))

    def get_state(self) -> NominalState:
        """Returns the current nominal state estimate."""
        return self._state.to_nominal_state()

    def get_covariance(self) -> np.ndarray:
        """Returns a copy of the current 15x15 error covariance matrix P."""
        return self._state.P.copy()

    def get_diagnostics(self) -> ESEKFDiagnostics:
        """Returns real-time filter health and uncertainty diagnostics."""
        return self._diagnostics.model_copy()

    def get_state_result(self) -> ESEKFStateResult:
        """Returns unified state estimate result with covariance diagonal and diagnostics."""
        return ESEKFStateResult(
            nominal_state=self.get_state(),
            covariance_diagonal=np.diag(self._state.P).tolist(),
            diagnostics=self.get_diagnostics(),
            is_valid=True,
        )
