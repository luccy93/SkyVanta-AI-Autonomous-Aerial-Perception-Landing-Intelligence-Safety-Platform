"""Dedicated authorization policy verifying safety invariants, flight modes, and command permissions."""

from typing import Optional, Tuple
from skyvanta.core.exceptions import CommandAuthorizationError
from skyvanta.core.types import (
    CommandSource,
    FlightCommand,
    FlightCommandType,
    FlightMode,
)


class CommandAuthorizationPolicy:
    """Evaluates whether a validated flight command is authorized for transmission to the autopilot."""

    def __init__(self, require_v7_authorization: bool = True):
        self.require_v7_authorization = require_v7_authorization

    def authorize(
        self,
        command: FlightCommand,
        current_flight_mode: FlightMode = FlightMode.GUIDED,
    ) -> Tuple[bool, Optional[str]]:
        """Determines if the command is permitted to execute in the current operational state.

        Args:
            command: FlightCommand instance to authorize.
            current_flight_mode: Current autopilot flight mode.

        Returns:
            (is_authorized, reason)
        """
        # 1. Connection check
        if current_flight_mode == FlightMode.DISCONNECTED:
            return False, "Cannot authorize command when autopilot is DISCONNECTED"

        # 2. Source authority check
        authorized_sources = {
            CommandSource.LANDING_INTELLIGENCE,
            CommandSource.SAFETY_SUPERVISOR,
            CommandSource.OPERATOR,
            CommandSource.SIMULATOR,
            CommandSource.TEST,
        }
        if command.source not in authorized_sources:
            return False, f"Unauthorized command source: {command.source}"

        # 3. Flight mode restrictions
        if current_flight_mode == FlightMode.FAILSAFE:
            allowed_in_failsafe = {FlightCommandType.HOLD, FlightCommandType.RECOVER, FlightCommandType.DISARM}
            if command.command_type not in allowed_in_failsafe:
                return False, f"Command {command.command_type.value} is prohibited in FAILSAFE mode"

        if current_flight_mode == FlightMode.ABORT:
            allowed_in_abort = {FlightCommandType.HOLD, FlightCommandType.RECOVER, FlightCommandType.ABORT, FlightCommandType.DISARM}
            if command.command_type not in allowed_in_abort:
                return False, f"Command {command.command_type.value} is prohibited in ABORT mode"

        # 4. Progression command safety validation
        progression_commands = {
            FlightCommandType.ALIGN,
            FlightCommandType.APPROACH,
            FlightCommandType.DESCEND,
            FlightCommandType.FINAL_APPROACH,
            FlightCommandType.CONFIRM_LANDING,
        }
        if command.command_type in progression_commands and self.require_v7_authorization:
            is_safe = command.parameters.get("is_safe_for_progression", False)
            if not is_safe:
                return False, (
                    f"Progression command {command.command_type.value} rejected: "
                    f"V7 safety supervisor did not grant progression clearance (is_safe_for_progression=False)"
                )

        return True, None

    def authorize_or_raise(
        self,
        command: FlightCommand,
        current_flight_mode: FlightMode = FlightMode.GUIDED,
    ) -> None:
        """Authorizes command and raises CommandAuthorizationError on failure."""
        is_auth, reason = self.authorize(command, current_flight_mode)
        if not is_auth:
            raise CommandAuthorizationError(f"Flight command authorization rejected: {reason}")
