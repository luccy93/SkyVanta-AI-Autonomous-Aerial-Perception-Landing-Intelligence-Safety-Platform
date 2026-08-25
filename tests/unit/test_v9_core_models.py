"""Unit tests for SimulationClock, Noise models, LatencyModel, and Dropout models."""

import pytest
import numpy as np

from skyvanta.simulation.clock import SimulationClock
from skyvanta.simulation.dropout import (
    FrameDropoutModel,
    FrameDropoutType,
    OcclusionModel,
    OcclusionType,
    SensorFaultModel,
    SensorFaultType,
    SensorType,
)
from skyvanta.simulation.latency import LatencyModel
from skyvanta.simulation.noise import (
    BiasNoise,
    GaussianNoise,
    RandomWalkNoise,
    UniformNoise,
)


def test_simulation_clock_step_and_pause():
    """Verifies deterministic discrete clock stepping and pause behavior."""
    clock = SimulationClock(start_time_sec=0.0, default_dt_sec=0.05)
    assert clock.current_time_sec == 0.0
    assert clock.step_count == 0

    t1 = clock.step()
    assert abs(t1 - 0.05) < 1e-6
    assert clock.step_count == 1

    clock.pause()
    t2 = clock.step()
    assert abs(t2 - 0.05) < 1e-6
    assert clock.step_count == 1

    clock.resume()
    t3 = clock.step(0.1)
    assert abs(t3 - 0.15) < 1e-6
    assert clock.step_count == 2

    clock.reset(start_time_sec=1.0)
    assert clock.current_time_sec == 1.0
    assert clock.step_count == 0


def test_gaussian_noise_determinism():
    """Verifies Gaussian noise produces identical sequences under identical seeds."""
    g1 = GaussianNoise(mean=0.0, sigma=1.0, seed=12345)
    g2 = GaussianNoise(mean=0.0, sigma=1.0, seed=12345)

    samples1 = [g1.sample() for _ in range(10)]
    samples2 = [g2.sample() for _ in range(10)]
    assert samples1 == samples2


def test_random_walk_drift():
    """Verifies random walk noise advances and accumulates drift over time."""
    rw = RandomWalkNoise(drift_rate=0.1, initial_value=0.0, seed=42)
    assert rw.sample() == 0.0

    rw.step(dt_sec=1.0)
    assert rw.sample() != 0.0


def test_uniform_and_bias_noise():
    """Verifies uniform and bias noise bounds."""
    u = UniformNoise(low=-2.0, high=5.0, seed=42)
    vec = u.sample_vec(20)
    assert np.all(vec >= -2.0)
    assert np.all(vec <= 5.0)

    b = BiasNoise(bias=3.14)
    assert b.sample() == 3.14
    assert np.all(b.sample_vec(5) == 3.14)


def test_latency_model_queue():
    """Verifies FIFO delayed sample delivery according to scheduled timestamps."""
    lat = LatencyModel(mean_latency_sec=0.1, jitter_sigma_sec=0.0, seed=42)
    lat.push("packet_1", current_time_sec=0.0)  # Ready at 0.1s
    lat.push("packet_2", current_time_sec=0.05) # Ready at 0.15s

    assert lat.pop_ready(current_time_sec=0.05) == []
    ready = lat.pop_ready(current_time_sec=0.12)
    assert ready == ["packet_1"]

    ready2 = lat.pop_ready(current_time_sec=0.2)
    assert ready2 == ["packet_2"]


def test_frame_dropout_patterns():
    """Verifies deterministic, periodic, and burst frame loss models."""
    drop_det = FrameDropoutModel(dropout_type=FrameDropoutType.DETERMINISTIC, drop_indices=[2, 5, 8])
    assert not drop_det.should_drop(1)
    assert drop_det.should_drop(2)
    assert drop_det.should_drop(5)

    drop_per = FrameDropoutModel(dropout_type=FrameDropoutType.PERIODIC, drop_period=10, drop_burst_length=2)
    assert drop_per.should_drop(0)
    assert drop_per.should_drop(1)
    assert not drop_per.should_drop(2)
    assert drop_per.should_drop(10)


def test_sensor_fault_model_and_occlusion():
    """Verifies scheduled sensor faults and target occlusion windows."""
    faults = SensorFaultModel()
    faults.add_fault(
        sensor_type=SensorType.CAMERA,
        fault_type=SensorFaultType.DROP,
        start_time_sec=2.0,
        end_time_sec=5.0,
    )
    assert faults.get_active_fault(SensorType.CAMERA, 1.0) is None
    active = faults.get_active_fault(SensorType.CAMERA, 3.0)
    assert active is not None
    assert active.fault_type == SensorFaultType.DROP

    occ = OcclusionModel(occlusion_type=OcclusionType.TEMPORARY, start_time_sec=1.5, duration_sec=2.0)
    assert not occ.is_occluded(1.0)
    assert occ.is_occluded(2.0)
    assert occ.is_occluded(3.5)
    assert not occ.is_occluded(4.0)
