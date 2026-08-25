"""Unit tests for TelemetryValidator."""

import pytest
from skyvanta.core.exceptions import FlightInterfaceError
from skyvanta.core.types import AutopilotTelemetry, FlightMode, FrameId
from skyvanta.flight.telemetry import TelemetryValidator


def test_telemetry_validator_accepts_valid_packet():
    """Verifies that a valid telemetry packet passes inspection."""
    validator = TelemetryValidator()
    telem = AutopilotTelemetry(
        timestamp_sec=10.0,
        is_connected=True,
        is_armed=True,
        flight_mode=FlightMode.GUIDED,
        position_m=(0.0, 0.0, 10.0),
        velocity_mps=(0.1, 0.0, -0.5),
        orientation_rpy_deg=(0.0, 0.0, 45.0),
        altitude_m=10.0,
        frame_id=FrameId.WORLD,
        is_simulation=True,
    )
    is_valid, reason = validator.validate(telem)
    assert is_valid is True
    assert reason is None


def test_telemetry_validator_rejects_excessive_speed():
    """Verifies rejection of unphysical vehicle velocity."""
    validator = TelemetryValidator(max_speed_mps=30.0)
    telem = AutopilotTelemetry(
        timestamp_sec=10.0,
        velocity_mps=(50.0, 0.0, 0.0),  # > 30 m/s
    )
    is_valid, reason = validator.validate(telem)
    assert is_valid is False
    assert "speed" in reason.lower()


def test_telemetry_validator_rejects_non_finite_values():
    """Verifies rejection of NaN or Inf numerical entries."""
    validator = TelemetryValidator()
    telem = AutopilotTelemetry(
        timestamp_sec=10.0,
        position_m=(float("nan"), 0.0, 10.0),
    )
    is_valid, reason = validator.validate(telem)
    assert is_valid is False
    assert "non-finite" in reason.lower()
