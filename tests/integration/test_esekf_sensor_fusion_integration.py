"""Deterministic integration tests for 15-state ESEKF sensor fusion pipeline (Volume 6)."""

import math
import numpy as np
import pytest

from skyvanta.core.config import ESEKFConfig
from skyvanta.core.types import FilterStatus
from skyvanta.fusion.filter import ErrorStateExtendedKalmanFilter
from skyvanta.fusion.metrics import StateEstimationMetrics
from skyvanta.fusion.simulation import SensorSimulator, SyntheticTrajectory


def test_end_to_end_stationary_sensor_fusion():
    """Verifies that ESEKF fuses 100 Hz IMU with 10 Hz visual updates to maintain accurate stationary hover."""
    traj = SyntheticTrajectory.stationary(
        duration_sec=3.0,
        dt_sec=0.01,
        position=(0.0, 0.0, -5.0),
    )
    sim = SensorSimulator(
        accel_noise_std=0.01,
        gyro_noise_std=0.001,
        visual_noise_std_m=0.02,
        random_seed=42,
    )

    filter_cfg = ESEKFConfig()
    filter_engine = ErrorStateExtendedKalmanFilter(filter_cfg)

    # Initialize at ground truth position
    filter_engine.initialize(
        position=(0.0, 0.0, -5.0),
        velocity=(0.0, 0.0, 0.0),
        rotation_matrix=np.eye(3),
        timestamp_sec=0.0,
    )

    estimates = []
    ground_truth = []

    for idx, gt_sample in enumerate(traj):
        # 1. IMU Propagation (every 10ms = 100 Hz)
        imu_meas = sim.generate_imu(gt_sample)
        filter_engine.propagate(imu_meas)

        # 2. Visual Update (every 50ms = 20 Hz)
        if idx % 5 == 0:
            vis_meas = sim.generate_visual_pose(gt_sample)
            filter_engine.update_visual(vis_meas)

        state = filter_engine.get_state()
        estimates.append({
            "position": state.position_world,
            "velocity": state.velocity_world,
            "rotation": state.rotation_matrix,
        })
        ground_truth.append({
            "position": gt_sample["position"],
            "velocity": gt_sample["velocity"],
            "rotation": gt_sample["rotation"],
        })

    metrics = StateEstimationMetrics.evaluate(estimates, ground_truth)

    # Position RMSE must be sub-decimeter (< 0.05m)
    assert metrics["position_rmse_m"] < 0.05
    # Velocity RMSE must be sub-0.1 m/s
    assert metrics["velocity_rmse_m_s"] < 0.10
    # Orientation RMSE must be under 1 degree
    assert metrics["orientation_rmse_deg"] < 1.0


def test_end_to_end_constant_velocity_fusion_with_outlier_rejection():
    """Verifies that ESEKF tracks dynamic trajectory and rejects injected visual outliers."""
    traj = SyntheticTrajectory.constant_velocity(
        duration_sec=3.0,
        dt_sec=0.01,
        initial_pos=(0.0, 0.0, -10.0),
        velocity=(1.0, 0.5, 0.1),
    )
    sim = SensorSimulator(random_seed=123)
    filter_engine = ErrorStateExtendedKalmanFilter()

    filter_engine.initialize(
        position=(0.0, 0.0, -10.0),
        velocity=(1.0, 0.5, 0.1),
        rotation_matrix=np.eye(3),
        timestamp_sec=0.0,
    )

    estimates = []
    ground_truth = []

    for idx, gt_sample in enumerate(traj):
        imu_meas = sim.generate_imu(gt_sample)
        filter_engine.propagate(imu_meas)

        if idx % 5 == 0:
            # Inject an outlier at step 100
            is_outlier = (idx == 100)
            vis_meas = sim.generate_visual_pose(gt_sample, is_outlier=is_outlier)
            filter_engine.update_visual(vis_meas)

        state = filter_engine.get_state()
        estimates.append({
            "position": state.position_world,
            "velocity": state.velocity_world,
            "rotation": state.rotation_matrix,
        })
        ground_truth.append({
            "position": gt_sample["position"],
            "velocity": gt_sample["velocity"],
            "rotation": gt_sample["rotation"],
        })

    diag = filter_engine.get_diagnostics()
    # At least 1 outlier must be rejected
    assert diag.rejected_measurement_count >= 1

    metrics = StateEstimationMetrics.evaluate(estimates, ground_truth)
    # Position tracking RMSE must remain stable (< 0.10m) despite outlier
    assert metrics["position_rmse_m"] < 0.10
