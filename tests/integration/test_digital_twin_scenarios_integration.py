"""Integration tests for DigitalTwin closed-loop simulation and batch scenario runner."""

import pytest
from skyvanta.core.types import ScenarioOutcome
from skyvanta.simulation.batch import BatchScenarioRunner
from skyvanta.simulation.engine import DigitalTwinEngine
from skyvanta.simulation.scenarios import ScenarioCatalog


def test_digital_twin_nominal_descent_execution():
    """Verifies that the digital twin executes a nominal descent scenario to successful landing."""
    engine = DigitalTwinEngine()
    scenario = ScenarioCatalog.nominal_descent()

    metrics, traj = engine.run_scenario(scenario, dt_sec=0.05)
    assert metrics.success is True
    assert metrics.outcome == ScenarioOutcome.SUCCESS_LANDED
    assert metrics.final_position_error_m < 0.3
    assert len(traj) > 0


def test_digital_twin_crosswind_descent_execution():
    """Verifies that the digital twin tracks and lands under turbulent crosswind gusts."""
    engine = DigitalTwinEngine()
    scenario = ScenarioCatalog.turbulent_crosswind()

    metrics, traj = engine.run_scenario(scenario, dt_sec=0.05)
    assert metrics.success is True
    assert metrics.outcome == ScenarioOutcome.SUCCESS_LANDED


def test_digital_twin_optical_occlusion_abort_execution():
    """Verifies that persistent optical occlusion triggers clean abort climb-out."""
    engine = DigitalTwinEngine()
    scenario = ScenarioCatalog.optical_occlusion_abort()

    metrics, traj = engine.run_scenario(scenario, dt_sec=0.05)
    assert metrics.success is True
    assert metrics.outcome in (ScenarioOutcome.SUCCESS_ABORTED, ScenarioOutcome.SUCCESS_RECOVERED)


def test_batch_scenario_runner_suite():
    """Verifies batch execution of the full scenario catalog and report generation."""
    runner = BatchScenarioRunner()
    # Run subset of scenarios for fast CI
    scenarios = [
        ScenarioCatalog.nominal_descent(),
        ScenarioCatalog.turbulent_crosswind(),
        ScenarioCatalog.optical_occlusion_abort(),
    ]
    summary = runner.run_suite(scenarios=scenarios, dt_sec=0.05)

    assert summary["total_scenarios"] == 3
    assert summary["passed_scenarios"] >= 2
    assert summary["pass_rate_percent"] >= 66.0

    report = BatchScenarioRunner.generate_markdown_report(summary)
    assert "# SkyVanta AI — Digital Twin Scenario Validation Report" in report
    assert "Overall Pass Rate" in report
