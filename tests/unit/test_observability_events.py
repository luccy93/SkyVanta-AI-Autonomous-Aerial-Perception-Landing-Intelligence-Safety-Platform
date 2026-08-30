"""Unit tests for structured event publishing, secret redaction, and bounded event buffers."""

import json
import logging
from skyvanta.deployment.observability.events import (
    EventLogger,
    EventType,
    StructuredEvent,
    redact_sensitive_data,
)


def test_redact_sensitive_data_nested_and_keys():
    """redact_sensitive_data must scrub credentials, passwords, tokens, and authorization headers."""
    raw_payload = {
        "scenario_name": "nominal_landing",
        "duration_ms": 42.5,
        "password": "super_secret_password_123",
        "api_key": "sk-1234567890abcdef",
        "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "headers": {
            "Authorization": "Bearer secret_jwt_token_9999",
            "Cookie": "session_id=abcdef123456; secure",
            "User-Agent": "SkyVanta-Client/1.0",
            "X-Request-ID": "req_12345",
        },
        "credentials": {
            "aws_secret_key": "AKIAIOSFODNN7EXAMPLE",
            "db_credential": "user:pass@host",
        },
        "items": [
            {"token": "item_token_1"},
            {"safe_key": "safe_val"},
        ],
        "log_message": "User authenticated with Bearer my_secret_token_123 successfully",
    }

    sanitized = redact_sensitive_data(raw_payload)

    # Verify non-sensitive data preserved
    assert sanitized["scenario_name"] == "nominal_landing"
    assert sanitized["duration_ms"] == 42.5
    assert sanitized["headers"]["User-Agent"] == "SkyVanta-Client/1.0"
    assert sanitized["headers"]["X-Request-ID"] == "req_12345"
    assert sanitized["items"][1]["safe_key"] == "safe_val"

    # Verify sensitive data replaced with [REDACTED]
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["auth_token"] == "[REDACTED]"
    assert sanitized["headers"]["Authorization"] == "[REDACTED]"
    assert sanitized["headers"]["Cookie"] == "[REDACTED]"
    assert sanitized["credentials"] == "[REDACTED]"
    assert sanitized["items"][0]["token"] == "[REDACTED]"
    assert "Bearer [REDACTED]" in sanitized["log_message"]
    assert "my_secret_token_123" not in sanitized["log_message"]


def test_event_logger_emit_and_bounded_buffer():
    """EventLogger must emit structured events and enforce circular buffer bounds."""
    logger = EventLogger(max_history=10)
    logger.clear()

    # Emit 15 events into buffer of capacity 10
    for i in range(15):
        logger.emit(
            event_type=EventType.SCENARIO_STARTED,
            message=f"Scenario step {i}",
            severity="INFO",
            details={"step_index": i, "secret_key": "sensitive_val"},
            environment="testing",
        )

    assert logger.history_size == 10
    events = logger.get_recent_events(limit=5)
    assert len(events) == 5
    # Last event should be step 14
    assert events[-1]["message"] == "Scenario step 14"
    assert events[-1]["details"]["step_index"] == 14
    assert events[-1]["details"]["secret_key"] == "[REDACTED]"


def test_event_logger_canonical_event_types():
    """EventLogger must support all standard Phase D7 event types."""
    logger = EventLogger(max_history=20)
    logger.clear()

    for et in EventType:
        ev = logger.emit(
            event_type=et,
            message=f"Event {et.value}",
            severity="INFO",
            details={"type": et.value},
            environment="testing",
        )
        assert isinstance(ev, StructuredEvent)
        assert ev.event_type == et
        assert ev.service == "skyvanta-api"
        assert ev.environment == "testing"
