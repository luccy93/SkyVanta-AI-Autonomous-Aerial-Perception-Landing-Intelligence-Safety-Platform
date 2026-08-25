"""Unit tests for SafetyViolationDetector, ScenarioEngine, Monte Carlo, Replay, and Determinism."""

import pytest
from skyvanta.core.types import (
    DigitalTwinState,
    LandingDecision,
    LandingPhase,
    RecommendedAction,
    SafetyReasonCode,
    SafetyViolation,
    ScenarioOutcome,
)
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.monte_carlo import MonteCarloRunner
from skyvanta.simulation.registry import ScenarioRegistry
from skyvanta.simulation.replay import ScenarioReplay
from skyvanta.simulation.safety import SafetyViolationDetector
from skyvanta.simulation.scenarios import compute_configuration_hash


def test_safety_violation_detector_high_landing_velocity():
    """Verifies safety detector catches excessive velocity at touchdown."""
    detector = SafetyViolationDetector(max_touchdown_velocity_mps=0.6)
    twin_state = DigitalTwinState(
        timestamp_sec=10.0,
        position_world=(0.0, 0.0, 0.0),
        velocity_world=(0.0, 0.0, -1.2),  # 1.2 m/s descent
        rotation_matrix=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        is_landed=True,
    )
    violations = detector.evaluate_step(
        twin_state=twin_state,
        decision=None,
        active_command=None,
        telemetry=None,
        current_time_sec=10.0,
    )
    assert len(violations) > 0
    assert violations[0].violation_type == SafetyViolation.LANDING_WITH_HIGH_VELOCITY


def test_scenario_registry_coverage():
    """Verifies all standard scenarios are registered and retrievable."""
    scenarios = ScenarioRegistry.list_all()
    assert len(scenarios) >= 12
    assert "nominal_landing" in scenarios
    assert "target_loss" in scenarios
    assert "target_occlusion" in scenarios
    assert "camera_dropout" in scenarios
    assert "imu_dropout" in scenarios
    assert "autopilot_disconnect" in scenarios


def test_scenario_engine_determinism():
    """Verifies that identical scenario + seed + config produces bitwise identical results."""
    scen = ScenarioRegistry.get("nominal_landing")
    assert scen is not None

    engine = ScenarioEngine()
    res1, traj1 = engine.run(scen, run_id="test_run_1")
    res2, traj2 = engine.run(scen, run_id="test_run_2")

    assert res1.status == res2.status
    assert res1.duration_sec == res2.duration_sec
    assert res1.metrics.final_position_error_m == res2.metrics.final_position_error_m
    assert res1.metrics.final_velocity_mps == res2.metrics.final_velocity_mps
    assert len(traj1) == len(traj2)


def test_monte_carlo_batch_reproducibility():
    """Verifies Monte Carlo runner computes consistent statistical aggregates."""
    scen = ScenarioRegistry.get("nominal_landing")
    assert scen is not None

    mc = MonteCarloRunner()
    stats, results = mc.run_batch(scen, number_of_runs=5, base_seed=500)
    assert stats.total_runs == 5
    assert len(results) == 5
    assert stats.success_rate >= 0.8


def test_scenario_replay_match():
    """Verifies ScenarioReplay successfully confirms match with baseline."""
    scen = ScenarioRegistry.get("nominal_landing")
    assert scen is not None

    engine = ScenarioEngine()
    baseline, _ = engine.run(scen, run_id="baseline_run")

    replay = ScenarioReplay(engine)
    is_match, mismatches = replay.replay_and_verify(scen, baseline)
    assert is_match is True
    assert len(mismatches) == 0
