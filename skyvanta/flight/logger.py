"""Structured machine-readable telemetry logger for flight interface events."""

import json
from typing import Any, Dict, Optional
from skyvanta.core.logging import get_logger
from skyvanta.core.types import (
    CommandAcknowledgement,
    FlightCommand,
    FlightMode,
)

logger = get_logger("skyvanta.flight.events")


class FlightEventLogger:
    """Formats and records structured flight interface events for auditability and diagnostics."""

    @staticmethod
    def format_event(
        event_type: str,
        timestamp_sec: float,
        command: Optional[FlightCommand] = None,
        ack: Optional[CommandAcknowledgement] = None,
        flight_mode: Optional[FlightMode] = None,
        reason: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Creates a standardized flight event dictionary."""
        event: Dict[str, Any] = {
            "timestamp": timestamp_sec,
            "event_type": event_type,
            "flight_mode": flight_mode.value if flight_mode else None,
            "reason": reason,
        }

        if command is not None:
            event["command_id"] = command.command_id
            event["sequence_number"] = command.sequence_number
            event["command_type"] = command.command_type.value
            event["source"] = command.source.value

        if ack is not None:
            event["ack_status"] = ack.status.value
            if ack.reason:
                event["ack_reason"] = ack.reason

        if kwargs:
            event["details"] = kwargs

        return event

    @classmethod
    def log_event(
        cls,
        event_type: str,
        timestamp_sec: float,
        command: Optional[FlightCommand] = None,
        ack: Optional[CommandAcknowledgement] = None,
        flight_mode: Optional[FlightMode] = None,
        reason: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Formats and logs the flight event to logger."""
        event = cls.format_event(
            event_type=event_type,
            timestamp_sec=timestamp_sec,
            command=command,
            ack=ack,
            flight_mode=flight_mode,
            reason=reason,
            **kwargs,
        )
        logger.info("Flight Event: %s", json.dumps(event))
        return event
