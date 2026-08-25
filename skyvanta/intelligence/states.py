"""Operational landing phase definitions, transition topologies, and semantics."""

from typing import Dict, List, Set
from skyvanta.core.types import LandingPhase, RecommendedAction


# Explicit state machine valid transition topology
VALID_TRANSITIONS: Dict[LandingPhase, Set[LandingPhase]] = {
    LandingPhase.IDLE: {LandingPhase.SEARCHING, LandingPhase.FAULT},
    LandingPhase.SEARCHING: {LandingPhase.TARGET_ACQUIRED, LandingPhase.ABORTING, LandingPhase.FAULT},
    LandingPhase.TARGET_ACQUIRED: {LandingPhase.ALIGNING, LandingPhase.SEARCHING, LandingPhase.ABORTING, LandingPhase.FAULT},
    LandingPhase.ALIGNING: {LandingPhase.APPROACHING, LandingPhase.TARGET_ACQUIRED, LandingPhase.ABORTING, LandingPhase.FAULT},
    LandingPhase.APPROACHING: {LandingPhase.DESCENDING, LandingPhase.ALIGNING, LandingPhase.ABORTING, LandingPhase.FAULT},
    LandingPhase.DESCENDING: {LandingPhase.FINAL_APPROACH, LandingPhase.ALIGNING, LandingPhase.ABORTING, LandingPhase.FAULT},
    LandingPhase.FINAL_APPROACH: {LandingPhase.LANDING_CONFIRMED, LandingPhase.ABORTING, LandingPhase.FAULT},
    LandingPhase.LANDING_CONFIRMED: {LandingPhase.IDLE, LandingPhase.FAULT},
    LandingPhase.ABORTING: {LandingPhase.RECOVERY, LandingPhase.FAULT, LandingPhase.IDLE},
    LandingPhase.RECOVERY: {LandingPhase.SEARCHING, LandingPhase.TARGET_ACQUIRED, LandingPhase.ABORTING, LandingPhase.FAULT},
    LandingPhase.FAULT: set(),  # Terminal until explicit software reset
}


PHASE_RECOMMENDED_ACTIONS: Dict[LandingPhase, RecommendedAction] = {
    LandingPhase.IDLE: RecommendedAction.HOLD,
    LandingPhase.SEARCHING: RecommendedAction.SEARCH,
    LandingPhase.TARGET_ACQUIRED: RecommendedAction.HOLD,
    LandingPhase.ALIGNING: RecommendedAction.ALIGN,
    LandingPhase.APPROACHING: RecommendedAction.APPROACH,
    LandingPhase.DESCENDING: RecommendedAction.CONTINUE_DESCENT,
    LandingPhase.FINAL_APPROACH: RecommendedAction.FINAL_APPROACH,
    LandingPhase.LANDING_CONFIRMED: RecommendedAction.CONFIRM_LANDING,
    LandingPhase.ABORTING: RecommendedAction.ABORT,
    LandingPhase.RECOVERY: RecommendedAction.RECOVER,
    LandingPhase.FAULT: RecommendedAction.FAULT,
}
