"""Unit tests for CommandAuthorizationPolicy."""

import pytest
from skyvanta.core.exceptions import CommandAuthorizationError
from skyvanta.core.types import (
    CommandSource,
    FlightCommand,
    FlightCommandType,
    FlightMode,
)
from skyvanta.flight.authorization import CommandAuthorizationPolicy


def test_authorization_granted_for_safe_command():
    """Verifies that an authorized safe command is permitted."""
    policy = CommandAuthorizationPolicy(require_v7_authorization=True)
    cmd = FlightCommand(
        command_id="CMD_000001",
        sequence_number=1,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
        parameters={"is_safe_for_progression": True},
    )
    is_auth, reason = policy.authorize(cmd, current_flight_mode=FlightMode.GUIDED)
    assert is_auth is True
    assert reason is None


def test_authorization_rejected_when_unsafe():
    """Verifies rejection of progression command when V7 flagged unsafe."""
    policy = CommandAuthorizationPolicy(require_v7_authorization=True)
    cmd = FlightCommand(
        command_id="CMD_000002",
        sequence_number=2,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
        parameters={"is_safe_for_progression": False},
    )
    is_auth, reason = policy.authorize(cmd, current_flight_mode=FlightMode.GUIDED)
    assert is_auth is False
    assert "progression clearance" in reason


def test_authorization_rejected_when_disconnected():
    """Verifies rejection when flight mode is DISCONNECTED."""
    policy = CommandAuthorizationPolicy()
    cmd = FlightCommand(
        command_id="CMD_000003",
        sequence_number=3,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.HOLD,
        source=CommandSource.OPERATOR,
    )
    is_auth, reason = policy.authorize(cmd, current_flight_mode=FlightMode.DISCONNECTED)
    assert is_auth is False
    assert "DISCONNECTED" in reason


def test_abort_command_allowed_in_abort_mode():
    """Verifies that ABORT / HOLD commands are permitted in ABORT mode."""
    policy = CommandAuthorizationPolicy()
    cmd = FlightCommand(
        command_id="CMD_000004",
        sequence_number=4,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.ABORT,
        source=CommandSource.SAFETY_SUPERVISOR,
    )
    is_auth, reason = policy.authorize(cmd, current_flight_mode=FlightMode.ABORT)
    assert is_auth is True
