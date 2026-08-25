"""Unit tests for the LandingStateMachine state transitions, timeouts, and latching."""

import pytest

from skyvanta.core.config import LandingIntelligenceConfig
from skyvanta.core.types import LandingPhase, RecommendedAction, SafetyReasonCode
from skyvanta.intelligence.fsm import LandingStateMachine
from skyvanta.intelligence.simulation import LandingScenarioSimulator


def test_fsm_initial_state():
    """Verifies default initial phase is SEARCHING."""
    fsm = LandingStateMachine()
    assert fsm.current_phase == LandingPhase.SEARCHING


def test_fsm_nominal_progression():
    """Verifies step-by-step nominal progression from SEARCHING to LANDING_CONFIRMED."""
    cfg = LandingIntelligenceConfig()
    cfg.confirmation.required_persistence_frames = 3
    fsm = LandingStateMachine(cfg)

    # 1. Step in SEARCHING with valid target -> TARGET_ACQUIRED
    ctx = LandingScenarioSimulator.create_context(timestamp_sec=1.0, target_pos_body=(0.1, 0.1, 10.0))
    dec1 = fsm.step(ctx)
    assert dec1.current_state == LandingPhase.TARGET_ACQUIRED

    # 2. Step in TARGET_ACQUIRED -> ALIGNING
    ctx = LandingScenarioSimulator.create_context(timestamp_sec=1.1, target_pos_body=(0.1, 0.1, 10.0))
    dec2 = fsm.step(ctx)
    assert dec2.current_state == LandingPhase.ALIGNING

    # 3. Step in ALIGNING with good alignment -> APPROACHING
    ctx = LandingScenarioSimulator.create_context(timestamp_sec=1.2, target_pos_body=(0.1, 0.1, 8.0))
    dec3 = fsm.step(ctx)
    assert dec3.current_state == LandingPhase.APPROACHING

    # 4. Step in APPROACHING -> DESCENDING
    ctx = LandingScenarioSimulator.create_context(timestamp_sec=1.3, target_pos_body=(0.1, 0.1, 5.0))
    dec4 = fsm.step(ctx)
    assert dec4.current_state == LandingPhase.DESCENDING

    # 5. Step in DESCENDING reaching final altitude (1.2m) -> FINAL_APPROACH
    ctx = LandingScenarioSimulator.create_context(timestamp_sec=1.4, target_pos_body=(0.05, 0.05, 1.2))
    dec5 = fsm.step(ctx)
    assert dec5.current_state == LandingPhase.FINAL_APPROACH

    # 6. Multi-frame persistence in FINAL_APPROACH for touchdown (alt <= 0.3m, vz <= 0.2m/s)
    # Frame 1: Persistence 1
    ctx = LandingScenarioSimulator.create_context(timestamp_sec=1.5, target_pos_body=(0.02, 0.02, 0.2), drone_velocity=(0.0, 0.0, 0.1))
    dec6 = fsm.step(ctx)
    assert dec6.current_state == LandingPhase.FINAL_APPROACH

    # Frame 2: Persistence 2
    ctx = LandingScenarioSimulator.create_context(timestamp_sec=1.6, target_pos_body=(0.02, 0.02, 0.2), drone_velocity=(0.0, 0.0, 0.1))
    dec7 = fsm.step(ctx)
    assert dec7.current_state == LandingPhase.FINAL_APPROACH

    # Frame 3: Persistence 3 -> LANDING_CONFIRMED!
    ctx = LandingScenarioSimulator.create_context(timestamp_sec=1.7, target_pos_body=(0.02, 0.02, 0.2), drone_velocity=(0.0, 0.0, 0.1))
    dec8 = fsm.step(ctx)
    assert dec8.current_state == LandingPhase.LANDING_CONFIRMED
    assert dec8.recommended_action == RecommendedAction.CONFIRM_LANDING


def test_fsm_target_loss_aborts_descent():
    """Verifies that dropping the target during descent triggers immediate ABORTING."""
    fsm = LandingStateMachine()
    # Fast forward to DESCENDING
    fsm._current_phase = LandingPhase.DESCENDING

    # Sudden target dropout
    ctx = LandingScenarioSimulator.create_context(timestamp_sec=2.0, target_valid=False)
    decision = fsm.step(ctx)

    assert decision.current_state == LandingPhase.ABORTING
    assert decision.recommended_action == RecommendedAction.ABORT
    assert decision.primary_reason == SafetyReasonCode.TARGET_NOT_FOUND


def test_fsm_latched_fault():
    """Verifies that critical fault transitions to FAULT and latches."""
    fsm = LandingStateMachine()
    ctx = LandingScenarioSimulator.create_context(timestamp_sec=1.0, critical_fault=True)

    dec1 = fsm.step(ctx)
    assert dec1.current_state == LandingPhase.FAULT
    assert dec1.recommended_action == RecommendedAction.FAULT

    # Subsequent nominal steps remain latched in FAULT
    ctx_nominal = LandingScenarioSimulator.create_context(timestamp_sec=1.1, critical_fault=False)
    dec2 = fsm.step(ctx_nominal)
    assert dec2.current_state == LandingPhase.FAULT
