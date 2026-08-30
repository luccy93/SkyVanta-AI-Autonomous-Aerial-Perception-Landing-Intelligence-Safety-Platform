"""Failure recovery manager, deterministic fault classification, and safety-gated recovery policies."""

from enum import Enum
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from skyvanta.core.exceptions import SkyVantaError
from skyvanta.deployment.reliability.startup import StartupValidationError

logger = logging.getLogger("skyvanta.reliability.recovery")


class FailureCategory(str, Enum):
    """Deterministic classification of application and system failure modes."""

    NORMAL_RESTART = "NORMAL_RESTART"
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    CONFIGURATION_FAILURE = "CONFIGURATION_FAILURE"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    SAFETY_CONFIGURATION_FAILURE = "SAFETY_CONFIGURATION_FAILURE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class RecoveryAction(str, Enum):
    """Automated recovery action prescribed by recovery policies."""

    RESTART_ALLOWED = "RESTART_ALLOWED"
    RETRY_WITH_BACKOFF = "RETRY_WITH_BACKOFF"
    BLOCK_RECOVERY = "BLOCK_RECOVERY"
    NO_ACTION = "NO_ACTION"


class RecoveryDecision(BaseModel):
    """Formal decision object prescribing recovery strategy and safety lock status."""

    category: FailureCategory = Field(
        description="Deterministic classification of the failure event.",
    )
    action: RecoveryAction = Field(
        description="Prescribed automated recovery action.",
    )
    recovery_blocked: bool = Field(
        description="Whether automatic recovery is blocked due to safety violations.",
    )
    reason: str = Field(
        description="Human and machine-readable explanation for recovery decision.",
    )
    backoff_sec: float = Field(
        default=0.0,
        ge=0.0,
        description="Recommended backoff delay before retry (0 if blocked or immediate).",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum permissible retry attempts.",
    )
    hardware_activation_prohibited: bool = Field(
        default=True,
        description="Strict safety invariant: Hardware activation is permanently disabled.",
    )


class RecoveryManager:
    """Classifies runtime failures and executes safety-bounded recovery decisions."""

    # Keywords associated with safety breaches
    _SAFETY_KEYWORDS = [
        "hardware",
        "allow_external",
        "allow_network_download",
        "hardware_disconnected",
        "serial",
        "mavlink",
        "actuator",
        "pwm",
    ]

    # Transient error types
    _TRANSIENT_EXCEPTIONS = (
        TimeoutError,
        ConnectionResetError,
        ConnectionRefusedError,
        BrokenPipeError,
    )

    def classify_failure(
        self,
        exception: Optional[BaseException] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailureCategory:
        """Deterministically classifies an exception or failure context.

        Classification Rules:
        1. Safety-related violations -> SAFETY_CONFIGURATION_FAILURE
        2. Startup validation or configuration errors -> CONFIGURATION_FAILURE
        3. Missing dependencies / empty registries -> DEPENDENCY_FAILURE
        4. Transient network/socket timeouts -> TRANSIENT_FAILURE
        5. Clean process termination -> NORMAL_RESTART
        6. Other unhandled exceptions -> UNKNOWN_FAILURE
        """
        ctx = context or {}

        # 1. Inspect for clean restart signals
        if ctx.get("clean_shutdown") or ctx.get("signal") in ("SIGTERM", "SIGINT"):
            return FailureCategory.NORMAL_RESTART

        if exception is None and not ctx:
            return FailureCategory.NORMAL_RESTART

        exc_str = (str(exception) if exception else "") + " " + str(ctx)
        exc_str_lower = exc_str.lower()

        # 2. Check for safety invariant breach keywords
        for keyword in self._SAFETY_KEYWORDS:
            if keyword in exc_str_lower and ("violat" in exc_str_lower or "true" in exc_str_lower or "enabled" in exc_str_lower):
                return FailureCategory.SAFETY_CONFIGURATION_FAILURE

        if isinstance(exception, StartupValidationError):
            if any(k in exc_str_lower for k in self._SAFETY_KEYWORDS):
                return FailureCategory.SAFETY_CONFIGURATION_FAILURE
            return FailureCategory.CONFIGURATION_FAILURE

        # 3. Check for general configuration failure
        if isinstance(exception, (ValueError, KeyError)) and ("config" in exc_str_lower or "env" in exc_str_lower):
            return FailureCategory.CONFIGURATION_FAILURE

        # 4. Check for dependency failure
        if isinstance(exception, (ImportError, ModuleNotFoundError)) or "registry" in exc_str_lower:
            return FailureCategory.DEPENDENCY_FAILURE

        # 5. Check for transient failure
        if isinstance(exception, self._TRANSIENT_EXCEPTIONS):
            return FailureCategory.TRANSIENT_FAILURE

        if "timeout" in exc_str_lower or "temporarily unavailable" in exc_str_lower:
            return FailureCategory.TRANSIENT_FAILURE

        return FailureCategory.UNKNOWN_FAILURE

    def evaluate_recovery(
        self,
        category: FailureCategory,
        retry_count: int = 0,
        custom_reason: Optional[str] = None,
    ) -> RecoveryDecision:
        """Evaluates recovery policy for a classified failure category.

        Strict Safety Policy:
        - NEVER attempt to automatically enable physical hardware.
        - For SAFETY_CONFIGURATION_FAILURE: Recovery is strictly BLOCKED.
        - For CONFIGURATION_FAILURE / DEPENDENCY_FAILURE: Recovery is BLOCKED (requires configuration fix).
        - For TRANSIENT_FAILURE: Retry allowed with exponential backoff if retry_count < max_retries.
        - For NORMAL_RESTART: Clean restart permitted.
        """
        if category == FailureCategory.SAFETY_CONFIGURATION_FAILURE:
            reason = custom_reason or (
                "Safety Invariant Violation detected. Automatic recovery is BLOCKED "
                "to maintain hardware isolation. Manual intervention required."
            )
            logger.critical("Recovery BLOCKED: %s", reason)
            return RecoveryDecision(
                category=category,
                action=RecoveryAction.BLOCK_RECOVERY,
                recovery_blocked=True,
                reason=reason,
                backoff_sec=0.0,
                max_retries=0,
                hardware_activation_prohibited=True,
            )

        if category == FailureCategory.CONFIGURATION_FAILURE:
            reason = custom_reason or (
                "Configuration error detected. Automatic restart blocked until configuration is corrected."
            )
            return RecoveryDecision(
                category=category,
                action=RecoveryAction.BLOCK_RECOVERY,
                recovery_blocked=True,
                reason=reason,
                backoff_sec=0.0,
                max_retries=0,
                hardware_activation_prohibited=True,
            )

        if category == FailureCategory.DEPENDENCY_FAILURE:
            reason = custom_reason or (
                "Required dependency or scenario catalog unavailable. Recovery is blocked."
            )
            return RecoveryDecision(
                category=category,
                action=RecoveryAction.BLOCK_RECOVERY,
                recovery_blocked=True,
                reason=reason,
                backoff_sec=0.0,
                max_retries=0,
                hardware_activation_prohibited=True,
            )

        if category == FailureCategory.TRANSIENT_FAILURE:
            max_retries = 3
            if retry_count < max_retries:
                backoff = min(30.0, 2.0 ** retry_count)
                reason = custom_reason or (
                    f"Transient failure detected. Retry permissible with {backoff}s backoff (Attempt {retry_count + 1}/{max_retries})."
                )
                return RecoveryDecision(
                    category=category,
                    action=RecoveryAction.RETRY_WITH_BACKOFF,
                    recovery_blocked=False,
                    reason=reason,
                    backoff_sec=backoff,
                    max_retries=max_retries,
                    hardware_activation_prohibited=True,
                )
            else:
                reason = f"Transient failure retries exhausted ({retry_count}/{max_retries}). Recovery blocked."
                return RecoveryDecision(
                    category=category,
                    action=RecoveryAction.BLOCK_RECOVERY,
                    recovery_blocked=True,
                    reason=reason,
                    backoff_sec=0.0,
                    max_retries=max_retries,
                    hardware_activation_prohibited=True,
                )

        if category == FailureCategory.NORMAL_RESTART:
            return RecoveryDecision(
                category=category,
                action=RecoveryAction.RESTART_ALLOWED,
                recovery_blocked=False,
                reason=custom_reason or "Normal clean process restart approved.",
                backoff_sec=0.0,
                max_retries=1,
                hardware_activation_prohibited=True,
            )

        # UNKNOWN_FAILURE fallback
        return RecoveryDecision(
            category=category,
            action=RecoveryAction.BLOCK_RECOVERY,
            recovery_blocked=True,
            reason=custom_reason or "Unclassified failure mode. Recovery blocked for safety.",
            backoff_sec=0.0,
            max_retries=0,
            hardware_activation_prohibited=True,
        )

    def handle_failure(
        self,
        exception: Optional[BaseException] = None,
        context: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> RecoveryDecision:
        """Convenience method combining classification and recovery evaluation."""
        category = self.classify_failure(exception=exception, context=context)
        return self.evaluate_recovery(category=category, retry_count=retry_count)


# Global singleton instance
recovery_manager = RecoveryManager()
