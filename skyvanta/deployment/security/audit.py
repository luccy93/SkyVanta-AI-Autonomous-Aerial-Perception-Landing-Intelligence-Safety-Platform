"""Structured security audit logging and immutable event recording."""

from collections import deque
from datetime import datetime, timezone
from enum import Enum
import json
import logging
import threading
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from skyvanta.deployment.security.redaction import sanitize_payload


class SecurityEventType(str, Enum):
    """Canonical security event types for audit tracking."""
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILURE = "AUTH_FAILURE"
    AUTH_REJECTED = "AUTH_REJECTED"
    KEY_REVOKED = "KEY_REVOKED"
    RATE_LIMITED = "RATE_LIMITED"
    FORBIDDEN = "FORBIDDEN"
    INVALID_REQUEST = "INVALID_REQUEST"
    WEBSOCKET_AUTH_FAILURE = "WEBSOCKET_AUTH_FAILURE"
    SECURITY_CONFIGURATION_ERROR = "SECURITY_CONFIGURATION_ERROR"


class SecurityAuditEvent(BaseModel):
    """Structured schema for non-sensitive security audit records."""

    event_type: SecurityEventType
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    severity: str = "INFO"
    client_ip: str = "unknown"
    path: str = "/"
    method: str = "GET"
    key_id: Optional[str] = None
    required_scope: Optional[str] = None
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    service: str = "skyvanta-api"


class SecurityAuditLogger:
    """Thread-safe security audit logger maintaining a bounded in-memory buffer."""

    def __init__(self, buffer_size: int = 200):
        self._lock = threading.RLock()
        self._buffer: deque = deque(maxlen=buffer_size)
        self._logger = logging.getLogger("skyvanta.security.audit")

    def record(
        self,
        event_type: SecurityEventType,
        message: str,
        severity: str = "INFO",
        client_ip: str = "unknown",
        path: str = "/",
        method: str = "GET",
        key_id: Optional[str] = None,
        required_scope: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> SecurityAuditEvent:
        """Emits and records a sanitized security audit event."""
        clean_details = sanitize_payload(details or {})

        event = SecurityAuditEvent(
            event_type=event_type,
            severity=severity.upper(),
            client_ip=client_ip,
            path=path,
            method=method,
            key_id=key_id,
            required_scope=required_scope,
            message=message,
            details=clean_details,
        )

        with self._lock:
            self._buffer.append(event)

        # Output structured JSON log to stdout logging pipeline
        log_func = getattr(self._logger, severity.lower(), self._logger.info)
        try:
            log_func(json.dumps(event.model_dump()))
        except Exception:
            pass

        return event

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent security audit events."""
        with self._lock:
            events = list(self._buffer)
            return [e.model_dump() for e in reversed(events[-limit:])]

    def clear(self) -> None:
        """Clears audit buffer (used in testing)."""
        with self._lock:
            self._buffer.clear()


# Global singleton security audit logger
security_audit_logger = SecurityAuditLogger()
