"""Translates Volume 7 LandingDecision contracts into Volume 8 FlightCommands."""

from typing import Dict, Optional
from skyvanta.core.config import CommandConfig
from skyvanta.core.types import (
    CommandSource,
    FlightCommand,
    FlightCommandType,
    LandingDecision,
    RecommendedAction,
)

# Mapping from V7 RecommendedAction to V8 FlightCommandType
ACTION_TO_COMMAND_MAP: Dict[RecommendedAction, FlightCommandType] = {
    RecommendedAction.HOLD: FlightCommandType.HOLD,
    RecommendedAction.SEARCH: FlightCommandType.SEARCH,
    RecommendedAction.ALIGN: FlightCommandType.ALIGN,
    RecommendedAction.APPROACH: FlightCommandType.APPROACH,
    RecommendedAction.CONTINUE_DESCENT: FlightCommandType.DESCEND,
    RecommendedAction.FINAL_APPROACH: FlightCommandType.FINAL_APPROACH,
    RecommendedAction.CONFIRM_LANDING: FlightCommandType.CONFIRM_LANDING,
    RecommendedAction.ABORT: FlightCommandType.ABORT,
    RecommendedAction.RECOVER: FlightCommandType.RECOVER,
    RecommendedAction.FAULT: FlightCommandType.HOLD,
}


class V7CommandTranslator:
    """Translates landing intelligence decisions into strongly typed flight commands."""

    def __init__(self, command_config: Optional[CommandConfig] = None):
        self.config = command_config or CommandConfig()
        self._sequence_counter: int = 1

    def translate(self, decision: LandingDecision) -> FlightCommand:
        """Converts a LandingDecision into a FlightCommand.

        Args:
            decision: Authorized LandingDecision emitted by the V7 Safety Supervisor.

        Returns:
            FlightCommand instance.
        """
        # Critical Safety Rule: ABORT action must NEVER produce normal descent
        if decision.recommended_action == RecommendedAction.ABORT:
            cmd_type = FlightCommandType.ABORT
        elif decision.recommended_action == RecommendedAction.FAULT:
            cmd_type = FlightCommandType.HOLD
        else:
            cmd_type = ACTION_TO_COMMAND_MAP.get(
                decision.recommended_action, FlightCommandType.HOLD
            )

        seq = self._sequence_counter
        self._sequence_counter += 1
        cmd_id = f"CMD_{seq:06d}"
        t_now = decision.timestamp_sec
        exp_time = t_now + self.config.expiry_sec

        params = {
            "decision_code": decision.decision_code,
            "current_phase": decision.current_state.value,
            "primary_reason": decision.primary_reason.value,
            "is_safe_for_progression": decision.is_safe_for_progression,
            "confidence": decision.confidence,
        }

        # Forward spatial guidance parameters if available
        if "vertical_distance_m" in decision.alignment_metrics:
            params["target_altitude_m"] = decision.alignment_metrics["vertical_distance_m"]
        if "lateral_error_m" in decision.alignment_metrics:
            params["lateral_error_m"] = decision.alignment_metrics["lateral_error_m"]
        if "yaw_error_deg" in decision.alignment_metrics:
            params["yaw_error_deg"] = decision.alignment_metrics["yaw_error_deg"]

        return FlightCommand(
            command_id=cmd_id,
            sequence_number=seq,
            timestamp_sec=t_now,
            expiration_sec=exp_time,
            command_type=cmd_type,
            source=CommandSource.LANDING_INTELLIGENCE,
            target_id=decision.target_id,
            parameters=params,
            is_valid=True,
        )

    def reset_sequence(self, initial_sequence: int = 1) -> None:
        """Resets the monotonic sequence counter."""
        self._sequence_counter = initial_sequence
