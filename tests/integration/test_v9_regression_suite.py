"""Integration regression test suite covering standard Volume 9 scenarios."""

import pytest
from skyvanta.core.types import ScenarioOutcome
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.registry import ScenarioRegistry


@pytest.mark.parametrize("scenario_name", [
    "nominal_landing",
    "target_loss",
    "target_occlusion",
    "camera_dropout",
    "imu_dropout",
    "autopilot_disconnect",
    "high_noise",
    "high_velocity",
    "high_uncertainty",
    "timing_failure",
    "estimator_degradation",
    "multiple_failures",
])
def test_v9_standard_scenario_execution(scenario_name: str):
    """Executes each standard scenario and asserts outcome matches safety requirement."""
    scenario = ScenarioRegistry.get(scenario_name)
    assert scenario is not None, f"Scenario '{scenario_name}' not found in registry"

    engine = ScenarioEngine()
    result, traj = engine.run(scenario)

    assert len(traj) > 0, "Scenario executed 0 steps"
    assert result.duration_sec > 0.0

    # Ensure no safety violation caused failure unless that was the specific design
    assert result.status != ScenarioOutcome.FAILED_SAFETY_VIOLATION, f"Unexpected safety violation in {scenario_name}: {result.safety_violations}"
    assert result.metrics.success is True, f"Scenario '{scenario_name}' failed pass criteria: outcome={result.status.value}"
