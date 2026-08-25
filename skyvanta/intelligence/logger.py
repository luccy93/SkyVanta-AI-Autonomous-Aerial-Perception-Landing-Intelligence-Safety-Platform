"""Structured machine-readable telemetry logger for landing decisions."""

import json
from typing import Any, Dict
from skyvanta.core.logging import get_logger
from skyvanta.core.types import LandingDecision

logger = get_logger("skyvanta.intelligence.decision")


class StructuredDecisionLogger:
    """Serializes landing decisions into structured, machine-readable telemetry events."""

    @staticmethod
    def format_event(decision: LandingDecision) -> Dict[str, Any]:
        """Converts a LandingDecision into a structured event dict."""
        event = {
            "timestamp": decision.timestamp_sec,
            "decision_code": decision.decision_code,
            "current_state": decision.current_state.value,
            "previous_state": decision.previous_state.value if decision.previous_state else None,
            "recommended_action": decision.recommended_action.value,
            "primary_reason": decision.primary_reason.value,
            "reason_codes": [r.value for r in decision.reason_codes],
            "is_safe": decision.is_safe_for_progression,
            "confidence": decision.confidence,
            "target_id": decision.target_id,
            "estimator_health": decision.estimator_health.value,
            "target_health": decision.target_health.value,
            "alignment": decision.alignment_metrics,
            "uncertainty": decision.uncertainty_metrics,
            "diagnostics": decision.diagnostics,
        }
        return event

    @classmethod
    def log_event(cls, decision: LandingDecision) -> None:
        """Logs the formatted decision event."""
        event = cls.format_event(decision)
        logger.info("Landing Decision Event: %s", json.dumps(event))
