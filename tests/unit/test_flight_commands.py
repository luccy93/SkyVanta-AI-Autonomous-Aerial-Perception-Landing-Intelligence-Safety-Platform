"""Unit tests for FlightCommand data model, priority scores, and enum representations."""

import pytest
from skyvanta.core.types import (
    CommandAcknowledgement,
    CommandSource,
    CommandStatus,
    FlightCommand,
    FlightCommandType,
    FlightMode,
)
from skyvanta.flight.commands import COMMAND_PRIORITIES, get_command_priority


def test_flight_command_creation():
    """Verifies creation of a valid FlightCommand instance."""
    cmd = FlightCommand(
        command_id="CMD_000001",
        sequence_number=1,
        timestamp_sec=10.0,
        expiration_sec=10.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
        target_id=1,
        parameters={"target_altitude_m": 5.0, "descent_rate_mps": 0.5},
    )
    assert cmd.command_id == "CMD_000001"
    assert cmd.sequence_number == 1
    assert cmd.command_type == FlightCommandType.DESCEND
    assert cmd.source == CommandSource.LANDING_INTELLIGENCE
    assert cmd.is_valid is True


def test_command_priorities_ordering():
    """Verifies that ABORT has the highest priority score followed by RECOVER and HOLD."""
    assert get_command_priority(FlightCommandType.ABORT) > get_command_priority(FlightCommandType.RECOVER)
    assert get_command_priority(FlightCommandType.RECOVER) > get_command_priority(FlightCommandType.HOLD)
    assert get_command_priority(FlightCommandType.HOLD) > get_command_priority(FlightCommandType.DESCEND)
    assert get_command_priority(FlightCommandType.DESCEND) > get_command_priority(FlightCommandType.SEARCH)


def test_command_acknowledgement_creation():
    """Verifies creation of a CommandAcknowledgement contract."""
    ack = CommandAcknowledgement(
        command_id="CMD_000001",
        sequence_number=1,
        status=CommandStatus.ACCEPTED,
        timestamp_sec=10.05,
        reason="Command accepted by autopilot",
    )
    assert ack.status == CommandStatus.ACCEPTED
    assert ack.sequence_number == 1
