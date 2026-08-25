"""Command transmission rate limiting and duplicate sequence suppression."""

from typing import Dict, Optional, Set, Tuple
from skyvanta.core.exceptions import RateLimitExceededError
from skyvanta.core.types import FlightCommand, FlightCommandType


class CommandRateLimiter:
    """Enforces minimum time intervals between commands and protects against duplicate transmissions."""

    def __init__(self, min_interval_sec: float = 0.05):
        self.min_interval_sec = min_interval_sec
        self._last_command_time: Dict[FlightCommandType, float] = {}
        self._seen_sequence_numbers: Set[int] = set()

    def check_rate_limit(self, command: FlightCommand, current_time_sec: float) -> Tuple[bool, Optional[str]]:
        """Evaluates whether the command complies with rate limiting and uniqueness constraints.

        Args:
            command: FlightCommand to inspect.
            current_time_sec: Current system time in seconds.

        Returns:
            (allowed, rejection_reason)
        """
        # Duplicate sequence number check
        if command.sequence_number in self._seen_sequence_numbers:
            return False, f"Duplicate command sequence number {command.sequence_number} already processed"

        # Safety commands (ABORT) bypass rate limiting for immediate flight safety
        if command.command_type == FlightCommandType.ABORT:
            return True, None

        # Rate limiting by command type
        last_t = self._last_command_time.get(command.command_type, None)
        if last_t is not None:
            elapsed = current_time_sec - last_t
            if elapsed < self.min_interval_sec:
                return False, (
                    f"Rate limit exceeded for {command.command_type.value}: "
                    f"elapsed {elapsed:.3f}s < minimum interval {self.min_interval_sec:.3f}s"
                )

        return True, None

    def record_command(self, command: FlightCommand, current_time_sec: float) -> None:
        """Records a successfully dispatched command into history."""
        self._last_command_time[command.command_type] = current_time_sec
        self._seen_sequence_numbers.add(command.sequence_number)

    def reset(self) -> None:
        """Clears all tracking history."""
        self._last_command_time.clear()
        self._seen_sequence_numbers.clear()
