"""Unit tests for FlightCommandValidator."""

import pytest
from skyvanta.core.exceptions import CommandValidationError
from skyvanta.core.types import CommandSource, FlightCommand, FlightCommandType
from skyvanta.flight.validation import FlightCommandValidator


def test_validator_accepts_valid_command():
    """Verifies that a well-formed command passes validation."""
    validator = FlightCommandValidator()
    cmd = FlightCommand(
        command_id="CMD_000001",
        sequence_number=1,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
    )
    is_valid, reason = validator.validate(cmd, current_time_sec=1.1)
    assert is_valid is True
    assert reason is None


def test_validator_rejects_expired_command():
    """Verifies that expired commands are rejected."""
    validator = FlightCommandValidator()
    cmd = FlightCommand(
        command_id="CMD_000002",
        sequence_number=2,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
    )
    is_valid, reason = validator.validate(cmd, current_time_sec=1.6)
    assert is_valid is False
    assert "expired" in reason.lower()


def test_validator_rejects_future_timestamp():
    """Verifies rejection of commands with excessive future timestamps."""
    validator = FlightCommandValidator(max_clock_skew_sec=1.0)
    cmd = FlightCommand(
        command_id="CMD_000003",
        sequence_number=3,
        timestamp_sec=5.0,
        expiration_sec=5.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
    )
    is_valid, reason = validator.validate(cmd, current_time_sec=1.0)
    assert is_valid is False
    assert "future" in reason.lower()


def test_validator_rejects_invalid_parameters():
    """Verifies rejection of invalid parameter bounds."""
    validator = FlightCommandValidator()
    cmd = FlightCommand(
        command_id="CMD_000004",
        sequence_number=4,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
        parameters={"descent_rate_mps": 10.0},  # > 5.0 m/s limit
    )
    is_valid, reason = validator.validate(cmd, current_time_sec=1.1)
    assert is_valid is False
    assert "descent rate" in reason.lower()
