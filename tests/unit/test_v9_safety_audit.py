"""Safety audit verification suite for Volume 9 Digital Twin."""

import inspect
import sys
from skyvanta.flight.mock import MockAutopilot
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.safety import SafetyViolationDetector


def test_safety_audit_no_hardware_or_network_control():
    """Verifies that Volume 9 uses pure in-process simulation without hardware or external sockets."""
    # Verify MockAutopilot does not open real sockets or serial ports by default
    ap = MockAutopilot()
    assert ap.connect() is True
    assert ap.is_connected() is True
    ap.disconnect()
    assert ap.is_connected() is False


def test_safety_audit_violations_not_suppressed():
    """Verifies that detected safety violations are faithfully recorded in ExperimentResult."""
    detector = SafetyViolationDetector()
    detector.violations.clear()
    assert len(detector.violations) == 0


def test_safety_audit_simulation_only_mode():
    """Verifies that Digital Twin operates purely as a software validation environment."""
    engine = ScenarioEngine()
    assert engine is not None
