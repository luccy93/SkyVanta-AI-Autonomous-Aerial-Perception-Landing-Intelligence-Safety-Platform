"""Unit tests for IMU measurement validation, timestamp processing, and gravity model."""

import numpy as np
import pytest

from skyvanta.core.config import GravityConfig
from skyvanta.core.exceptions import SensorTimingError
from skyvanta.core.types import FrameId, IMUMeasurement
from skyvanta.fusion.imu import GravityModel, IMUPreprocessor


def test_gravity_model_default():
    """Verifies default gravitational acceleration vector in NED frame."""
    gravity = GravityModel()
    g_vec = gravity.gravity_vector
    assert g_vec.shape == (3,)
    np.testing.assert_allclose(g_vec, [0.0, 0.0, 9.80665], atol=1e-5)


def test_gravity_model_custom():
    """Verifies custom gravitational magnitude and direction."""
    cfg = GravityConfig(magnitude_m_s2=9.78, direction=[0.0, 0.0, -1.0])
    gravity = GravityModel(cfg)
    np.testing.assert_allclose(gravity.gravity_vector, [0.0, 0.0, -9.78], atol=1e-5)


def test_imu_preprocessor_nominal_dt():
    """Verifies nominal dt calculation across consecutive IMU samples."""
    preprocessor = IMUPreprocessor(min_dt_sec=0.001, max_dt_sec=0.10)

    m1 = IMUMeasurement(
        timestamp_sec=1.00,
        angular_velocity_rad_s=(0.0, 0.0, 0.0),
        linear_acceleration_m_s2=(0.0, 0.0, -9.80665),
    )
    dt1 = preprocessor.validate_and_compute_dt(m1)
    assert dt1 > 0.0

    m2 = IMUMeasurement(
        timestamp_sec=1.01,
        angular_velocity_rad_s=(0.0, 0.0, 0.0),
        linear_acceleration_m_s2=(0.0, 0.0, -9.80665),
    )
    dt2 = preprocessor.validate_and_compute_dt(m2)
    assert pytest.approx(dt2, abs=1e-6) == 0.01


def test_imu_preprocessor_rejects_duplicate_or_backwards_timestamp():
    """Verifies that backwards or duplicate timestamps raise SensorTimingError."""
    preprocessor = IMUPreprocessor(min_dt_sec=0.001, max_dt_sec=0.10)

    m1 = IMUMeasurement(
        timestamp_sec=2.00,
        angular_velocity_rad_s=(0.0, 0.0, 0.0),
        linear_acceleration_m_s2=(0.0, 0.0, -9.80665),
    )
    preprocessor.validate_and_compute_dt(m1)

    m_backwards = IMUMeasurement(
        timestamp_sec=1.99,
        angular_velocity_rad_s=(0.0, 0.0, 0.0),
        linear_acceleration_m_s2=(0.0, 0.0, -9.80665),
    )
    with pytest.raises(SensorTimingError):
        preprocessor.validate_and_compute_dt(m_backwards)


def test_imu_preprocessor_rejects_excessive_gap():
    """Verifies that excessive time gaps raise SensorTimingError."""
    preprocessor = IMUPreprocessor(min_dt_sec=0.001, max_dt_sec=0.10)

    m1 = IMUMeasurement(
        timestamp_sec=1.00,
        angular_velocity_rad_s=(0.0, 0.0, 0.0),
        linear_acceleration_m_s2=(0.0, 0.0, -9.80665),
    )
    preprocessor.validate_and_compute_dt(m1)

    m_late = IMUMeasurement(
        timestamp_sec=1.50,  # 0.5s gap > max 0.10s
        angular_velocity_rad_s=(0.0, 0.0, 0.0),
        linear_acceleration_m_s2=(0.0, 0.0, -9.80665),
    )
    with pytest.raises(SensorTimingError):
        preprocessor.validate_and_compute_dt(m_late)
