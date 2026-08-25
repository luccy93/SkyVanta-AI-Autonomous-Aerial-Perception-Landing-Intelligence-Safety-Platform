"""Strict structural, temporal, and semantic validation for flight commands."""

from typing import Optional, Tuple
from skyvanta.core.exceptions import CommandValidationError
from skyvanta.core.types import CommandSource, FlightCommand, FlightCommandType


class FlightCommandValidator:
    """Validates structural correctness, timing constraints, and parameter bounds of flight commands."""

    def __init__(self, max_clock_skew_sec: float = 1.0):
        self.max_clock_skew_sec = max_clock_skew_sec

    def validate(self, command: FlightCommand, current_time_sec: float) -> Tuple[bool, Optional[str]]:
        """Evaluates command validity.

        Args:
            command: FlightCommand instance to inspect.
            current_time_sec: Current system time in seconds.

        Returns:
            (is_valid, rejection_reason)
        """
        # 1. Structural checks
        if not command.command_id or not command.command_id.strip():
            return False, "Command ID cannot be empty"

        if command.sequence_number < 0:
            return False, f"Invalid negative sequence number: {command.sequence_number}"

        # 2. Timing and clock skew checks
        if command.timestamp_sec <= 0.0:
            return False, f"Invalid non-positive timestamp: {command.timestamp_sec}"

        if command.timestamp_sec > current_time_sec + self.max_clock_skew_sec:
            return False, (
                f"Command timestamp {command.timestamp_sec:.3f} is in the future relative to "
                f"current time {current_time_sec:.3f} (skew > {self.max_clock_skew_sec}s)"
            )

        # 3. Expiration checks
        if current_time_sec > command.expiration_sec:
            return False, (
                f"Command expired: current time {current_time_sec:.3f} > "
                f"expiration time {command.expiration_sec:.3f}"
            )

        # 4. Command type & source checks
        if not isinstance(command.command_type, FlightCommandType):
            return False, f"Unsupported command type: {command.command_type}"

        if not isinstance(command.source, CommandSource):
            return False, f"Unsupported command source: {command.source}"

        # 5. Parameter sanity bounds
        params = command.parameters
        if "target_altitude_m" in params:
            alt = params["target_altitude_m"]
            if alt < 0.0 or alt > 500.0:
                return False, f"Target altitude {alt}m is out of valid bounds [0.0, 500.0]"

        if "descent_rate_mps" in params:
            rate = params["descent_rate_mps"]
            if rate <= 0.0 or rate > 5.0:
                return False, f"Descent rate {rate}m/s is out of valid bounds (0.0, 5.0]"

        return True, None

    def validate_or_raise(self, command: FlightCommand, current_time_sec: float) -> None:
        """Validates command and raises CommandValidationError on failure."""
        is_valid, reason = self.validate(command, current_time_sec)
        if not is_valid:
            raise CommandValidationError(f"Flight command validation failed: {reason}")
