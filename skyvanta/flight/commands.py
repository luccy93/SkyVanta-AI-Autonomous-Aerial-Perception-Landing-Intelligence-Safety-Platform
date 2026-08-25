"""High-level flight command representations and priority classifications."""

from typing import Dict
from skyvanta.core.types import (
    CommandAcknowledgement,
    CommandSource,
    CommandStatus,
    FlightCommand,
    FlightCommandType,
    FlightMode,
)

# Deterministic command priority ordering (higher numerical value = higher preemptive priority)
COMMAND_PRIORITIES: Dict[FlightCommandType, int] = {
    FlightCommandType.ABORT: 100,
    FlightCommandType.RECOVER: 90,
    FlightCommandType.HOLD: 80,
    FlightCommandType.CONFIRM_LANDING: 70,
    FlightCommandType.FINAL_APPROACH: 60,
    FlightCommandType.DESCEND: 50,
    FlightCommandType.APPROACH: 40,
    FlightCommandType.ALIGN: 30,
    FlightCommandType.SEARCH: 20,
    FlightCommandType.DISARM: 10,
}


def get_command_priority(cmd_type: FlightCommandType) -> int:
    """Returns the priority score for a given command type."""
    return COMMAND_PRIORITIES.get(cmd_type, 0)
