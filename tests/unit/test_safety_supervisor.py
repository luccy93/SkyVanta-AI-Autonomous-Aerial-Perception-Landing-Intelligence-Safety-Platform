"""Unit tests for independent safety invariant evaluations and priority ordering."""

import pytest

from skyvanta.core.config import LandingIntelligenceConfig
from skyvanta.core.types import (
    EstimatorHealthStatus,
    LandingPhase,
    SafetyReasonCode,
    TargetHealthStatus,
)
from skyvanta.intelligence.health import evaluate_estimator_health, evaluate_target_health
from skyvanta.intelligence.simulation import LandingScenarioSimulator
from skyvanta.intelligence.supervisor import SafetySupervisor


def test_safety_supervisor_nominal_conditions():
    """Verifies that nominal inputs produce is_safe=True with NOMINAL_CONDITIONS."""
    supervisor = SafetySupervisor()
    ctx = LandingScenarioSimulator.create_context(
        timestamp_sec=1.0,
        target_pos_body=(0.1, 0.1, 5.0),
        target_yaw_deg=2.0,
        drone_velocity=(0.2, 0.1, 0.1),
        position_3sigma_m=0.05,
    )

    is_safe, primary, all_reasons, metadata = supervisor.evaluate_safety(ctx, LandingPhase.ALIGNING)
    assert is_safe is True
    assert primary == SafetyReasonCode.NOMINAL_CONDITIONS
    assert len(all_reasons) == 0


def test_safety_supervisor_target_lost():
    """Verifies that missing target is caught with TARGET_NOT_FOUND."""
    supervisor = SafetySupervisor()
    ctx = LandingScenarioSimulator.create_context(
        timestamp_sec=1.0,
        target_valid=False,
    )

    is_safe, primary, all_reasons, metadata = supervisor.evaluate_safety(ctx, LandingPhase.ALIGNING)
    assert is_safe is False
    assert primary == SafetyReasonCode.TARGET_NOT_FOUND


def test_safety_supervisor_high_uncertainty():
    """Verifies that high 3-sigma position uncertainty triggers POSITION_UNCERTAINTY_HIGH."""
    supervisor = SafetySupervisor()
    ctx = LandingScenarioSimulator.create_context(
        timestamp_sec=1.0,
        position_3sigma_m=1.2,  # exceeds default 0.5m limit
    )

    is_safe, primary, all_reasons, metadata = supervisor.evaluate_safety(ctx, LandingPhase.ALIGNING)
    assert is_safe is False
    assert SafetyReasonCode.POSITION_UNCERTAINTY_HIGH in all_reasons


def test_safety_supervisor_excessive_velocity():
    """Verifies that horizontal speed exceeding limits triggers VELOCITY_TOO_HIGH."""
    supervisor = SafetySupervisor()
    ctx = LandingScenarioSimulator.create_context(
        timestamp_sec=1.0,
        drone_velocity=(3.5, 0.0, 0.0),  # > 2.0 m/s max horizontal
    )

    is_safe, primary, all_reasons, metadata = supervisor.evaluate_safety(ctx, LandingPhase.ALIGNING)
    assert is_safe is False
    assert SafetyReasonCode.VELOCITY_TOO_HIGH in all_reasons


def test_safety_supervisor_priority_ordering():
    """Verifies deterministic hierarchy: Critical Fault > Estimator > Target > Uncertainty > Velocity > Alignment."""
    supervisor = SafetySupervisor()

    # Scenario: Simultaneous target lost + high velocity + high uncertainty
    ctx = LandingScenarioSimulator.create_context(
        timestamp_sec=1.0,
        target_valid=False,
        drone_velocity=(4.0, 0.0, 0.0),
        position_3sigma_m=1.5,
    )

    is_safe, primary, all_reasons, metadata = supervisor.evaluate_safety(ctx, LandingPhase.ALIGNING)
    assert is_safe is False
    # Target lost has higher priority than velocity or alignment
    assert primary == SafetyReasonCode.TARGET_NOT_FOUND

    # Add critical hardware fault
    ctx_fault = LandingScenarioSimulator.create_context(
        timestamp_sec=1.0,
        target_valid=False,
        critical_fault=True,
    )
    is_safe, primary_fault, _, _ = supervisor.evaluate_safety(ctx_fault, LandingPhase.ALIGNING)
    assert primary_fault == SafetyReasonCode.CRITICAL_FAULT
