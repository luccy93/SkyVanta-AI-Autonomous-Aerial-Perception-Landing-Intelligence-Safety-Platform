"""Deterministic integration tests for Landing Intelligence State Machine & Safety Supervisor (Volume 7)."""

import math
import numpy as np
import pytest

from skyvanta.core.config import LandingIntelligenceConfig
from skyvanta.core.types import (
    LandingPhase,
    LandingSafetyContext,
    Pose6D,
    PoseEstimateResult,
    RecommendedAction,
    SafetyReasonCode,
)
from skyvanta.fusion.filter import ErrorStateExtendedKalmanFilter
from skyvanta.fusion.simulation import SensorSimulator, SyntheticTrajectory
from skyvanta.intelligence.fsm import LandingStateMachine
from skyvanta.intelligence.logger import StructuredDecisionLogger
from skyvanta.intelligence.simulation import LandingScenarioSimulator


def test_end_to_end_landing_intelligence_pipeline():
    """Verifies complete end-to-end flow from synthetic perception -> ESEKF -> Safety Supervisor -> Decision."""
    # 1. Initialize ESEKF
    ekf = ErrorStateExtendedKalmanFilter()
    ekf.initialize(
        position=(0.0, 0.0, -10.0),
        velocity=(0.0, 0.0, 0.0),
        rotation_matrix=np.eye(3),
        timestamp_sec=0.0,
    )

    # 2. Initialize Landing State Machine
    fsm_cfg = LandingIntelligenceConfig()
    fsm_cfg.confirmation.required_persistence_frames = 3
    fsm = LandingStateMachine(fsm_cfg)

    # Step 1: Initial search (t=0.05) -> Target not yet acquired -> remains SEARCHING
    ctx_search = LandingSafetyContext(
        timestamp_sec=0.05,
        pose_result=None,
        esekf_state=ekf.get_state(),
        esekf_diagnostics=ekf.get_diagnostics(),
    )
    dec1 = fsm.step(ctx_search)
    assert dec1.current_state == LandingPhase.SEARCHING
    assert dec1.recommended_action == RecommendedAction.SEARCH

    # Step 2: Target Acquired (t=0.10)
    ctx_acquired = LandingScenarioSimulator.create_context(
        timestamp_sec=0.10,
        target_pos_body=(0.1, 0.1, 8.0),
    )
    dec2 = fsm.step(ctx_acquired)
    assert dec2.current_state == LandingPhase.TARGET_ACQUIRED

    # Step 3: Aligning (t=0.15)
    ctx_align = LandingScenarioSimulator.create_context(
        timestamp_sec=0.15,
        target_pos_body=(0.1, 0.1, 8.0),
    )
    dec3 = fsm.step(ctx_align)
    assert dec3.current_state == LandingPhase.ALIGNING

    # Step 4: Approaching (t=0.20)
    ctx_app = LandingScenarioSimulator.create_context(
        timestamp_sec=0.20,
        target_pos_body=(0.05, 0.05, 5.0),
    )
    dec4 = fsm.step(ctx_app)
    assert dec4.current_state == LandingPhase.APPROACHING

    # Step 5: Descending (t=0.25)
    ctx_desc = LandingScenarioSimulator.create_context(
        timestamp_sec=0.25,
        target_pos_body=(0.02, 0.02, 3.0),
    )
    dec5 = fsm.step(ctx_desc)
    assert dec5.current_state == LandingPhase.DESCENDING
    assert dec5.recommended_action == RecommendedAction.CONTINUE_DESCENT

    # Verify structured decision logger produces valid JSON
    event = StructuredDecisionLogger.format_event(dec5)
    assert event["current_state"] == "DESCENDING"
    assert event["recommended_action"] == "CONTINUE_DESCENT"
    assert event["is_safe"] is True


def test_target_dropout_abort_and_recovery_flow():
    """Verifies that target loss triggers ABORTING -> RECOVERY -> SEARCHING upon reacquisition."""
    fsm = LandingStateMachine()

    # Fast-forward to DESCENDING
    fsm._current_phase = LandingPhase.DESCENDING

    # 1. Target dropout at t=1.0 -> ABORTING
    ctx_lost = LandingScenarioSimulator.create_context(timestamp_sec=1.0, target_valid=False)
    dec_abort = fsm.step(ctx_lost)
    assert dec_abort.current_state == LandingPhase.ABORTING
    assert dec_abort.recommended_action == RecommendedAction.ABORT

    # 2. Next step at t=1.1 -> RECOVERY
    ctx_rec = LandingScenarioSimulator.create_context(timestamp_sec=1.1, target_valid=False)
    dec_rec = fsm.step(ctx_rec)
    assert dec_rec.current_state == LandingPhase.RECOVERY
    assert dec_rec.recommended_action == RecommendedAction.RECOVER

    # 3. Target reacquired at t=1.2 -> TARGET_ACQUIRED
    ctx_reacq = LandingScenarioSimulator.create_context(timestamp_sec=1.2, target_valid=True)
    dec_reacq = fsm.step(ctx_reacq)
    assert dec_reacq.current_state == LandingPhase.TARGET_ACQUIRED
