"""Unit tests for ScenarioCatalog and ScenarioDefinition."""

import pytest
from skyvanta.core.types import ScenarioOutcome
from skyvanta.simulation.scenarios import ScenarioCatalog, ScenarioDefinition


def test_scenario_catalog_coverage():
    """Verifies all required predefined scenarios are present in the catalog."""
    suite = ScenarioCatalog.get_full_suite()
    assert len(suite) >= 6

    names = {s.name for s in suite}
    assert "NOMINAL_VERTICAL_DESCENT" in names
    assert "TURBULENT_CROSSWIND_DESCENT" in names
    assert "OPTICAL_OCCLUSION_ABORT" in names
    assert "TARGET_REACQUISITION_RECOVERY" in names
    assert "LOW_VISIBILITY_HIGH_NOISE" in names
    assert "MOVING_LANDING_PAD" in names


def test_scenario_definition_properties():
    """Verifies scenario definition structure."""
    sc = ScenarioCatalog.nominal_descent()
    assert sc.name == "NOMINAL_VERTICAL_DESCENT"
    assert sc.expected_outcome == ScenarioOutcome.SUCCESS_LANDED
    assert sc.initial_drone_pos[2] > 0.0
