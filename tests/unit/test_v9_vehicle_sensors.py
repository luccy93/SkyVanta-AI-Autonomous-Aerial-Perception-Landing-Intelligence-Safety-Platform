"""Unit tests for SimulatedVehicle, SimulatedLandingTarget, SimulatedCamera, and SimulatedIMU."""

import pytest
import numpy as np

from skyvanta.core.types import FlightCommand, FlightCommandType
from skyvanta.simulation.camera import SimulatedCamera
from skyvanta.simulation.disturbances import DisturbanceEvent, DisturbanceModel
from skyvanta.simulation.imu import SimulatedIMU
from skyvanta.simulation.target import SimulatedLandingTarget
from skyvanta.simulation.vehicle import SimulatedVehicle


def test_simulated_vehicle_kinematics_and_commands():
    """Verifies vehicle kinematic integration, altitude bounds, and command tracking."""
    vehicle = SimulatedVehicle(initial_position=(0.0, 0.0, 5.0), initial_velocity=(0.0, 0.0, 0.0))
    assert vehicle.position[2] == 5.0
    assert not vehicle.is_landed

    # Command Descend
    cmd_descend = FlightCommand(
        command_id="CMD_001",
        sequence_number=1,
        timestamp_sec=0.1,
        expiration_sec=10.0,
        command_type=FlightCommandType.DESCEND,
    )

    state = vehicle.step(
        dt_sec=0.1,
        current_time_sec=0.1,
        active_command=cmd_descend,
        target_pad_position=(0.0, 0.0, 0.0),
    )
    # Velocity Z should be negative (descending)
    assert vehicle.velocity[2] < 0.0
    assert state.position_world[2] < 5.0


def test_simulated_landing_target_corners():
    """Verifies 3D metric corner coordinates of stationary and moving landing targets."""
    target_stat = SimulatedLandingTarget(marker_size_m=1.0, initial_position=(2.0, 1.0, 0.0))
    corners = target_stat.get_3d_corners_world(timestamp_sec=0.0)
    assert corners.shape == (4, 3)
    # Center should be at (2.0, 1.0, 0.0)
    center = np.mean(corners, axis=0)
    assert np.allclose(center, [2.0, 1.0, 0.0])

    target_mov = SimulatedLandingTarget(
        marker_size_m=1.0,
        initial_position=(0.0, 0.0, 0.0),
        velocity_mps=(1.0, 0.0, 0.0),
    )
    pos_2s = target_mov.get_position_at(timestamp_sec=2.0)
    assert np.allclose(pos_2s, [2.0, 0.0, 0.0])


def test_simulated_camera_projection():
    """Verifies camera projects target 3D corners to 2D image coordinates and detects FOV."""
    camera = SimulatedCamera(pixel_noise_sigma=0.0, seed=42)
    target = SimulatedLandingTarget(marker_size_m=0.8, initial_position=(0.0, 0.0, 0.0))

    drone_pos = np.array([0.0, 0.0, 4.0])
    drone_R = np.eye(3)

    obs = camera.capture_target_observation(
        drone_pos_world=drone_pos,
        drone_R_world=drone_R,
        target=target,
        current_time_sec=0.0,
    )
    assert obs is not None
    pixels, detection, corners_cam = obs
    assert pixels.shape == (4, 2)
    assert detection.confidence > 0.9
    assert detection.bbox.is_valid()


def test_simulated_imu_specific_force():
    """Verifies synthetic IMU computes body specific force including gravity."""
    imu = SimulatedIMU(accel_noise_sigma=0.0, gyro_noise_sigma=0.0, seed=42)
    drone_accel = np.array([0.0, 0.0, 0.0])  # Hovering
    drone_R = np.eye(3)
    drone_omega = np.array([0.0, 0.0, 0.0])

    meas = imu.generate_measurement(
        drone_accel_world=drone_accel,
        drone_R_world=drone_R,
        drone_omega_body=drone_omega,
        current_time_sec=0.0,
    )
    assert meas is not None
    # For stationary drone, specific force magnitude equals gravity magnitude
    assert abs(abs(meas.linear_acceleration_m_s2[2]) - 9.81) < 0.1
