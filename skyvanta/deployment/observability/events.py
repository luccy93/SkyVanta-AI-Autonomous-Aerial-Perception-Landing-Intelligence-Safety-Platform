"""Structured operational events, JSON serialization, and secret redaction."""

from collections import deque
from datetime import datetime, timezone
from enum import Enum
import json
import logging
import re
from typing import Any, Deque, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Canonical operational lifecycle and diagnostic event types."""
    SERVICE_STARTED = "SERVICE_STARTED"
    SERVICE_READY = "SERVICE_READY"
    SERVICE_SHUTDOWN = "SERVICE_SHUTDOWN"
    REQUEST_ERROR = "REQUEST_ERROR"
    SCENARIO_STARTED = "SCENARIO_STARTED"
    SCENARIO_COMPLETED = "SCENARIO_COMPLETED"
    SCENARIO_FAILED = "SCENARIO_FAILED"
    WEBSOCKET_CONNECTED = "WEBSOCKET_CONNECTED"
    WEBSOCKET_DISCONNECTED = "WEBSOCKET_DISCONNECTED"
    HEARTBEAT_FAILURE = "HEARTBEAT_FAILURE"
    RESOURCE_WARNING = "RESOURCE_WARNING"
    SLOW_REQUEST = "SLOW_REQUEST"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|passwd|secret|token|auth|authorization|cookie|set-cookie|api[_-]?key|credential|private[_-]?key)",
    re.IGNORECASE,
)

_BEARER_PATTERN = re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE)


def redact_sensitive_data(data: Any) -> Any:
    """Recursively redacts sensitive credentials, tokens, cookies, and keys.

    Args:
        data: Arbitrary data structure (dict, list, string, primitive).

    Returns:
        Sanitized data structure with sensitive values replaced with '[REDACTED]'.
    """
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            str_key = str(k)
            if _SENSITIVE_KEY_PATTERN.search(str_key):
                sanitized[str_key] = "[REDACTED]"
            else:
                sanitized[str_key] = redact_sensitive_data(v)
        return sanitized
    elif isinstance(data, list):
        return [redact_sensitive_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(redact_sensitive_data(item) for item in data)
    elif isinstance(data, str):
        if _BEARER_PATTERN.search(data):
            return _BEARER_PATTERN.sub("Bearer [REDACTED]", data)
        return data
    else:
        return data


class StructuredEvent(BaseModel):
    """Machine-readable operational event schema."""

    event_type: EventType = Field(description="Canonical event classifier.")
    timestamp: str = Field(description="ISO-8601 UTC timestamp.")
    severity: str = Field(default="INFO", description="Log severity (DEBUG, INFO, WARNING, ERROR).")
    message: str = Field(description="Human-readable diagnostic summary.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Sanitized diagnostic metadata.")
    service: str = Field(default="skyvanta-api", description="Service identifier.")
    environment: str = Field(default="production", description="Deployment environment tier.")


class EventLogger:
    """Publishes structured operational events with bounded in-memory audit history."""

    def __init__(self, max_history: int = 100, logger_name: str = "skyvanta.events"):
        self._history: Deque[StructuredEvent] = deque(maxlen=max(10, max_history))
        self._logger = logging.getLogger(logger_name)

    @property
    def history_size(self) -> int:
        """Returns the current number of events stored in the bounded history."""
        return len(self._history)

    def emit(
        self,
        event_type: Union[EventType, str],
        message: str,
        severity: str = "INFO",
        details: Optional[Dict[str, Any]] = None,
        environment: str = "production",
    ) -> StructuredEvent:
        """Emits a structured operational event, logs to stdout, and stores in bounded history.

        Args:
            event_type: Canonical event identifier.
            message: Descriptive diagnostic message.
            severity: Severity level (INFO, WARNING, ERROR).
            details: Optional contextual metadata (will be automatically sanitized).
            environment: Deployment tier name.

        Returns:
            StructuredEvent instance.
        """
        if isinstance(event_type, str):
            try:
                e_type = EventType(event_type)
            except ValueError:
                e_type = EventType.REQUEST_ERROR
        else:
            e_type = event_type

        cleaned_details = redact_sensitive_data(details or {})
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        event = StructuredEvent(
            event_type=e_type,
            timestamp=now_utc,
            severity=severity.upper(),
            message=message,
            details=cleaned_details,
            service="skyvanta-api",
            environment=environment,
        )

        # Store in bounded circular buffer
        self._history.append(event)

        # Output to logging pipeline
        log_method = getattr(self._logger, severity.lower(), self._logger.info)
        payload = event.model_dump()
        log_method(json.dumps(payload))

        return event

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent events from the bounded buffer in chronological order."""
        events = list(self._history)
        if limit > 0:
            events = events[-limit:]
        return [e.model_dump() for e in events]

    def clear(self) -> None:
        """Clears the internal event buffer (used in tests)."""
        self._history.clear()


# Global default event logger singleton
event_logger = EventLogger(max_history=100)
