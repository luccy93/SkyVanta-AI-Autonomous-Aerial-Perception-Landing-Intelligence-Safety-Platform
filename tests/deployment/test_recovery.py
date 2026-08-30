"""Unit tests for RecoveryManager and failure classification policies."""

import pytest

from skyvanta.deployment.reliability.recovery import (
    FailureCategory,
    RecoveryAction,
    RecoveryDecision,
    RecoveryManager,
)
from skyvanta.deployment.reliability.startup import StartupValidationError


def test_failure_classification():
    """Verifies deterministic classification of various error modes."""
    mgr = RecoveryManager()

    # Normal restart
    assert mgr.classify_failure(context={"clean_shutdown": True}) == FailureCategory.NORMAL_RESTART
    assert mgr.classify_failure(context={"signal": "SIGTERM"}) == FailureCategory.NORMAL_RESTART

    # Safety violation
    safety_exc = StartupValidationError("Safety Violation: allow_external is True")
    assert mgr.classify_failure(safety_exc) == FailureCategory.SAFETY_CONFIGURATION_FAILURE

    # Configuration error
    cfg_exc = ValueError("Invalid environment configuration parameter")
    assert mgr.classify_failure(cfg_exc) == FailureCategory.CONFIGURATION_FAILURE

    # Dependency error
    dep_exc = ImportError("Missing scenario registry dependency")
    assert mgr.classify_failure(dep_exc) == FailureCategory.DEPENDENCY_FAILURE

    # Transient error
    timeout_exc = TimeoutError("Connection temporarily timed out")
    assert mgr.classify_failure(timeout_exc) == FailureCategory.TRANSIENT_FAILURE

    # Unknown error
    assert mgr.classify_failure(Exception("Arbitrary unhandled bug")) == FailureCategory.UNKNOWN_FAILURE


def test_safety_failure_blocks_recovery():
    """Verifies that SAFETY_CONFIGURATION_FAILURE triggers hard recovery lock."""
    mgr = RecoveryManager()
    decision = mgr.evaluate_recovery(FailureCategory.SAFETY_CONFIGURATION_FAILURE)

    assert decision.action == RecoveryAction.BLOCK_RECOVERY
    assert decision.recovery_blocked is True
    assert decision.hardware_activation_prohibited is True
    assert decision.max_retries == 0


def test_transient_failure_backoff():
    """Verifies exponential backoff and retry limits on transient failures."""
    mgr = RecoveryManager()

    # Attempt 0 (first retry)
    dec0 = mgr.evaluate_recovery(FailureCategory.TRANSIENT_FAILURE, retry_count=0)
    assert dec0.action == RecoveryAction.RETRY_WITH_BACKOFF
    assert dec0.recovery_blocked is False
    assert dec0.backoff_sec == 1.0
    assert dec0.hardware_activation_prohibited is True

    # Attempt 2
    dec2 = mgr.evaluate_recovery(FailureCategory.TRANSIENT_FAILURE, retry_count=2)
    assert dec2.action == RecoveryAction.RETRY_WITH_BACKOFF
    assert dec2.backoff_sec == 4.0

    # Exhausted retries (attempt 3)
    dec3 = mgr.evaluate_recovery(FailureCategory.TRANSIENT_FAILURE, retry_count=3)
    assert dec3.action == RecoveryAction.BLOCK_RECOVERY
    assert dec3.recovery_blocked is True


def test_hardware_activation_always_prohibited():
    """Verifies that hardware activation is permanently prohibited across all decisions."""
    mgr = RecoveryManager()
    for cat in FailureCategory:
        dec = mgr.evaluate_recovery(cat)
        assert dec.hardware_activation_prohibited is True
