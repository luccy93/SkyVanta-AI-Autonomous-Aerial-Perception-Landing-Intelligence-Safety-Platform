"""Unit tests for V7CommandTranslator."""

import pytest
from skyvanta.core.types import (
    FlightCommandType,
    LandingDecision,
    LandingPhase,
    RecommendedAction,
    SafetyReasonCode,
)
from skyvanta.flight.translation import V7CommandTranslator


def test_translation_continue_descent_to_descend():
    """Verifies that CONTINUE_DESCENT maps to FlightCommandType.DESCEND."""
    translator = V7CommandTranslator()
    dec = LandingDecision(
        timestamp_sec=1.0,
        current_state=LandingPhase.DESCENDING,
        recommended_action=RecommendedAction.CONTINUE_DESCENT,
        decision_code="DEC_0001",
        primary_reason=SafetyReasonCode.NOMINAL_CONDITIONS,
        is_safe_for_progression=True,
        confidence=0.95,
        alignment_metrics={"vertical_distance_m": 3.0, "lateral_error_m": 0.1},
    )
    cmd = translator.translate(dec)
    assert cmd.command_type == FlightCommandType.DESCEND
    assert cmd.sequence_number == 1
    assert cmd.parameters["target_altitude_m"] == 3.0


def test_translation_abort_safety_invariant():
    """Critical safety check: ABORT decision MUST NEVER produce a DESCEND command."""
    translator = V7CommandTranslator()
    dec = LandingDecision(
        timestamp_sec=2.0,
        current_state=LandingPhase.ABORTING,
        recommended_action=RecommendedAction.ABORT,
        decision_code="DEC_0002",
        primary_reason=SafetyReasonCode.TARGET_NOT_FOUND,
        is_safe_for_progression=False,
        confidence=0.0,
    )
    cmd = translator.translate(dec)
    assert cmd.command_type == FlightCommandType.ABORT
    assert cmd.command_type != FlightCommandType.DESCEND


def test_translation_monotonic_sequence_increment():
    """Verifies sequence numbers strictly increment across sequential translations."""
    translator = V7CommandTranslator()
    dec = LandingDecision(
        timestamp_sec=1.0,
        current_state=LandingPhase.ALIGNING,
        recommended_action=RecommendedAction.ALIGN,
        decision_code="DEC_0003",
        primary_reason=SafetyReasonCode.NOMINAL_CONDITIONS,
        is_safe_for_progression=True,
    )
    cmd1 = translator.translate(dec)
    cmd2 = translator.translate(dec)
    assert cmd2.sequence_number == cmd1.sequence_number + 1
