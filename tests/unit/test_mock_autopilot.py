"""Unit tests for MockAutopilot simulator."""

import pytest
from skyvanta.core.types import (
    CommandSource,
    CommandStatus,
    FlightCommand,
    FlightCommandType,
    FlightMode,
)
from skyvanta.flight.mock import MockAutopilot


def test_mock_autopilot_connection_lifecycle():
    """Verifies connect and disconnect state transitions."""
    ap = MockAutopilot()
    assert ap.is_connected() is False
    assert ap._flight_mode == FlightMode.DISCONNECTED

    ap.connect()
    assert ap.is_connected() is True
    assert ap._flight_mode == FlightMode.STANDBY

    ap.disconnect()
    assert ap.is_connected() is False
    assert ap._flight_mode == FlightMode.DISCONNECTED


def test_mock_autopilot_descend_kinematics():
    """Verifies that DESCEND command reduces simulated altitude."""
    ap = MockAutopilot(initial_position=(0.0, 0.0, 10.0))
    ap.connect()

    cmd = FlightCommand(
        command_id="CMD_000001",
        sequence_number=1,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
    )
    ack = ap.send_command(cmd)
    assert ack.status == CommandStatus.ACCEPTED
    assert ap._flight_mode == FlightMode.LANDING

    # Step simulation 2 seconds (0.5 m/s descent -> 1.0m altitude reduction)
    ap.step(dt=2.0)
    telem = ap.receive_telemetry()
    assert telem is not None
    assert pytest.approx(telem.altitude_m, rel=1e-2) == 9.0


def test_mock_autopilot_abort_climb():
    """Verifies that ABORT command transitions to ABORT mode and increases altitude."""
    ap = MockAutopilot(initial_position=(0.0, 0.0, 5.0))
    ap.connect()

    cmd = FlightCommand(
        command_id="CMD_000002",
        sequence_number=2,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.ABORT,
        source=CommandSource.SAFETY_SUPERVISOR,
    )
    ack = ap.send_command(cmd)
    assert ack.status == CommandStatus.ACCEPTED
    assert ap._flight_mode == FlightMode.ABORT

    # Step simulation 2 seconds (1.0 m/s climb -> 2.0m increase)
    ap.step(dt=2.0)
    telem = ap.receive_telemetry()
    assert telem is not None
    assert pytest.approx(telem.altitude_m, rel=1e-2) == 7.0


def test_mock_autopilot_fault_injection():
    """Verifies fault injection for testing timeout and rejection paths."""
    ap = MockAutopilot()
    ap.connect()

    ap.set_fault_injection(force_timeout=True)
    cmd = FlightCommand(
        command_id="CMD_000003",
        sequence_number=3,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.HOLD,
        source=CommandSource.OPERATOR,
    )
    ack = ap.send_command(cmd)
    assert ack.status == CommandStatus.TIMEOUT
