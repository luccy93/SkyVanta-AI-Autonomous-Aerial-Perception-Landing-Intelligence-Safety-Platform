"""Unit tests for SyntheticSensorSuite."""

import numpy as np
import pytest

from skyvanta.simulation.sensors import SyntheticSensorSuite


def test_sensor_suite_generate_pose():
    """Verifies synthetic camera pose estimation generation."""
    sensors = SyntheticSensorSuite(pixel_noise_std=0.0)
    drone_pos = np.array([0.0, 0.0, 5.0])
    drone_R = np.eye(3)
    pad_pos = np.array([0.0, 0.0, 0.0])

    res = sensors.generate_pose_estimate(
        drone_pos_world=drone_pos,
        drone_R_world=drone_R,
        pad_pos_world=pad_pos,
        t_sec=1.0,
    )
    assert res is not None
    assert res.is_valid is True
    assert res.pose is not None
    assert pytest.approx(res.pose.range_m, rel=1e-2) == 5.0


def test_sensor_suite_occlusion():
    """Verifies that occlusion produces None pose output."""
    sensors = SyntheticSensorSuite()
    res = sensors.generate_pose_estimate(
        drone_pos_world=np.array([0.0, 0.0, 5.0]),
        drone_R_world=np.eye(3),
        pad_pos_world=np.array([0.0, 0.0, 0.0]),
        t_sec=1.0,
        is_occluded=True,
    )
    assert res is None


def test_sensor_suite_generate_imu():
    """Verifies IMU packet generation."""
    sensors = SyntheticSensorSuite(accel_noise_std=0.0, gyro_noise_std=0.0)
    imu = sensors.generate_imu(
        drone_accel_world=np.zeros(3),
        drone_R_world=np.eye(3),
        drone_omega_body=np.zeros(3),
        t_sec=1.0,
    )
    # Stationary drone specific force is -gravity (Z = -9.80665 m/s^2)
    assert pytest.approx(imu.linear_acceleration_m_s2[2], rel=1e-2) == -9.80665

