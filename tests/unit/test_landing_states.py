"""Unit tests for landing phases, valid transition topology, and action mappings."""

import pytest

from skyvanta.core.types import LandingPhase, RecommendedAction
from skyvanta.intelligence.states import PHASE_RECOMMENDED_ACTIONS, VALID_TRANSITIONS


def test_landing_phase_enum_values():
    """Verifies all required landing phase enum values are present."""
    expected = {
        "IDLE",
        "SEARCHING",
        "TARGET_ACQUIRED",
        "ALIGNING",
        "APPROACHING",
        "DESCENDING",
        "FINAL_APPROACH",
        "LANDING_CONFIRMED",
        "ABORTING",
        "RECOVERY",
        "FAULT",
    }
    actual = {phase.value for phase in LandingPhase}
    assert expected == actual


def test_phase_recommended_actions():
    """Verifies each landing phase has an associated recommended supervisory action."""
    for phase in LandingPhase:
        assert phase in PHASE_RECOMMENDED_ACTIONS
        assert isinstance(PHASE_RECOMMENDED_ACTIONS[phase], RecommendedAction)


def test_valid_transitions_coverage():
    """Verifies transition table defines valid targets for every phase."""
    for phase in LandingPhase:
        assert phase in VALID_TRANSITIONS
        assert isinstance(VALID_TRANSITIONS[phase], set)
