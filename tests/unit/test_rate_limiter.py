"""Unit tests for CommandRateLimiter."""

import pytest
from skyvanta.core.types import CommandSource, FlightCommand, FlightCommandType
from skyvanta.flight.rate_limiter import CommandRateLimiter


def test_rate_limiter_allows_spaced_commands():
    """Verifies that commands separated by >= min_interval are permitted."""
    limiter = CommandRateLimiter(min_interval_sec=0.05)
    cmd1 = FlightCommand(
        command_id="CMD_000001",
        sequence_number=1,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
    )
    ok1, reason1 = limiter.check_rate_limit(cmd1, current_time_sec=1.0)
    assert ok1 is True
    limiter.record_command(cmd1, current_time_sec=1.0)

    cmd2 = FlightCommand(
        command_id="CMD_000002",
        sequence_number=2,
        timestamp_sec=1.06,
        expiration_sec=1.56,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
    )
    ok2, reason2 = limiter.check_rate_limit(cmd2, current_time_sec=1.06)
    assert ok2 is True


def test_rate_limiter_rejects_rapid_duplicate_type():
    """Verifies rejection when commands arrive faster than min_interval."""
    limiter = CommandRateLimiter(min_interval_sec=0.05)
    cmd1 = FlightCommand(
        command_id="CMD_000001",
        sequence_number=1,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
    )
    limiter.record_command(cmd1, current_time_sec=1.0)

    cmd2 = FlightCommand(
        command_id="CMD_000002",
        sequence_number=2,
        timestamp_sec=1.01,
        expiration_sec=1.51,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
    )
    ok2, reason2 = limiter.check_rate_limit(cmd2, current_time_sec=1.01)
    assert ok2 is False
    assert "Rate limit exceeded" in reason2


def test_rate_limiter_abort_bypasses_rate_limit():
    """Verifies that safety-critical ABORT commands bypass rate limits."""
    limiter = CommandRateLimiter(min_interval_sec=0.05)
    cmd_desc = FlightCommand(
        command_id="CMD_000001",
        sequence_number=1,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
    )
    limiter.record_command(cmd_desc, current_time_sec=1.0)

    cmd_abort = FlightCommand(
        command_id="CMD_000002",
        sequence_number=2,
        timestamp_sec=1.005,
        expiration_sec=1.505,
        command_type=FlightCommandType.ABORT,
        source=CommandSource.SAFETY_SUPERVISOR,
    )
    ok, reason = limiter.check_rate_limit(cmd_abort, current_time_sec=1.005)
    assert ok is True
