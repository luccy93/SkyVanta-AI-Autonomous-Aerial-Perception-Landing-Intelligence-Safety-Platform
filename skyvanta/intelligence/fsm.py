"""Landing intelligence finite state machine governing phase progression, timeouts, and latching."""

import time
from typing import List, Optional
import numpy as np

from skyvanta.core.config import LandingIntelligenceConfig
from skyvanta.core.exceptions import InvalidStateTransitionError
from skyvanta.core.logging import get_logger
from skyvanta.core.types import (
    EstimatorHealthStatus,
    LandingDecision,
    LandingPhase,
    LandingSafetyContext,
    RecommendedAction,
    SafetyReasonCode,
    TargetHealthStatus,
)
from skyvanta.intelligence.states import PHASE_RECOMMENDED_ACTIONS, VALID_TRANSITIONS
from skyvanta.intelligence.supervisor import SafetySupervisor

logger = get_logger("skyvanta.intelligence.fsm")


class LandingStateMachine:
    """Finite state machine with transition guards, temporal debouncing, and safety supervision."""

    def __init__(self, config: Optional[LandingIntelligenceConfig] = None):
        self.config = config or LandingIntelligenceConfig()
        self.supervisor = SafetySupervisor(self.config)

        self._current_phase: LandingPhase = LandingPhase.SEARCHING
        self._previous_phase: Optional[LandingPhase] = None
        self._phase_start_time_sec: float = 0.0
        self._persistence_frame_count: int = 0
        self._latched_fault: bool = False
        self._decision_sequence_id: int = 0

    @property
    def current_phase(self) -> LandingPhase:
        """Returns the active operational landing phase."""
        return self._current_phase

    def reset(self, initial_phase: LandingPhase = LandingPhase.SEARCHING) -> None:
        """Resets state machine history and clears latched fault."""
        self._current_phase = initial_phase
        self._previous_phase = None
        self._phase_start_time_sec = 0.0
        self._persistence_frame_count = 0
        self._latched_fault = False
        self._decision_sequence_id = 0
        logger.info("Landing state machine reset to phase: %s", initial_phase.value)

    def step(self, context: LandingSafetyContext) -> LandingDecision:
        """Executes a single discrete supervisory decision cycle."""
        self._decision_sequence_id += 1
        t_sec = context.timestamp_sec

        if self._phase_start_time_sec <= 0.0:
            self._phase_start_time_sec = t_sec

        phase_duration_sec = t_sec - self._phase_start_time_sec

        # 1. Evaluate Latched Fault
        if self._latched_fault or self._current_phase == LandingPhase.FAULT:
            return self._build_decision(
                context=context,
                phase=LandingPhase.FAULT,
                action=RecommendedAction.FAULT,
                primary_reason=SafetyReasonCode.CRITICAL_FAULT,
                reasons=[SafetyReasonCode.CRITICAL_FAULT],
                is_safe=False,
                confidence=0.0,
            )

        # 2. Check State Timeouts
        timeout_triggered, timeout_reason = self._check_state_timeout(phase_duration_sec)
        if timeout_triggered:
            next_phase = LandingPhase.ABORTING if self._current_phase != LandingPhase.RECOVERY else LandingPhase.FAULT
            if next_phase == LandingPhase.FAULT:
                self._latched_fault = True
            self._transition_to(next_phase, t_sec)
            return self._build_decision(
                context=context,
                phase=self._current_phase,
                action=PHASE_RECOMMENDED_ACTIONS[self._current_phase],
                primary_reason=timeout_reason,
                reasons=[timeout_reason],
                is_safe=False,
                confidence=0.0,
            )

        # 3. Handle Active Aborting State
        if self._current_phase == LandingPhase.ABORTING:
            self._transition_to(LandingPhase.RECOVERY, t_sec)
            return self._build_decision(
                context=context,
                phase=LandingPhase.RECOVERY,
                action=RecommendedAction.RECOVER,
                primary_reason=SafetyReasonCode.NOMINAL_CONDITIONS,
                reasons=[],
                is_safe=False,
                confidence=0.5,
            )

        # 4. Evaluate Safety Invariants
        is_safe, primary_reason, all_reasons, metadata = self.supervisor.evaluate_safety(
            context=context,
            current_phase=self._current_phase,
        )

        # 5. Handle Safety Violations & Abort Progression
        if not is_safe:
            if primary_reason == SafetyReasonCode.CRITICAL_FAULT:
                self._latched_fault = True
                self._transition_to(LandingPhase.FAULT, t_sec)
            elif self._current_phase in (
                LandingPhase.TARGET_ACQUIRED,
                LandingPhase.ALIGNING,
                LandingPhase.APPROACHING,
                LandingPhase.DESCENDING,
                LandingPhase.FINAL_APPROACH,
            ):
                self._transition_to(LandingPhase.ABORTING, t_sec)

            self._persistence_frame_count = 0
            return self._build_decision(
                context=context,
                phase=self._current_phase,
                action=PHASE_RECOMMENDED_ACTIONS[self._current_phase],
                primary_reason=primary_reason,
                reasons=all_reasons,
                is_safe=False,
                confidence=0.1,
                metadata=metadata,
            )

        # 6. Safe Phase Progression Engine
        next_phase = self._evaluate_progression(context, metadata)
        if next_phase != self._current_phase:
            self._transition_to(next_phase, t_sec)

        return self._build_decision(
            context=context,
            phase=self._current_phase,
            action=PHASE_RECOMMENDED_ACTIONS[self._current_phase],
            primary_reason=SafetyReasonCode.NOMINAL_CONDITIONS,
            reasons=[],
            is_safe=True,
            confidence=0.95,
            metadata=metadata,
        )


    def _evaluate_progression(self, context: LandingSafetyContext, metadata: dict) -> LandingPhase:
        """Determines if the system satisfies transition guards to progress into the next landing phase."""
        alignment = metadata.get("alignment", {})
        uncertainty = metadata.get("uncertainty", {})

        if self._current_phase == LandingPhase.SEARCHING:
            # Requires valid target acquisition
            if context.pose_result is not None and context.pose_result.is_valid:
                return LandingPhase.TARGET_ACQUIRED

        elif self._current_phase == LandingPhase.TARGET_ACQUIRED:
            # Target acquired -> transition to ALIGNING
            return LandingPhase.ALIGNING

        elif self._current_phase == LandingPhase.ALIGNING:
            # Transition to APPROACHING when aligned within thresholds
            if (
                alignment.get("lateral_error_m", 999.0) <= self.config.alignment.max_lateral_error_m
                and alignment.get("yaw_error_deg", 999.0) <= self.config.alignment.max_yaw_error_deg
            ):
                return LandingPhase.APPROACHING

        elif self._current_phase == LandingPhase.APPROACHING:
            # Transition to DESCENDING when approach envelope is verified
            if (
                alignment.get("horizontal_distance_m", 999.0) <= self.config.alignment.max_lateral_error_m
                and alignment.get("horizontal_speed_mps", 999.0) <= self.config.velocity.max_horizontal_speed_mps
            ):
                return LandingPhase.DESCENDING

        elif self._current_phase == LandingPhase.DESCENDING:
            # Transition to FINAL_APPROACH when within final altitude window (< 1.5m)
            alt = alignment.get("vertical_distance_m", 999.0)
            if alt <= 1.5:
                return LandingPhase.FINAL_APPROACH

        elif self._current_phase == LandingPhase.FINAL_APPROACH:
            # Evaluate landing confirmation persistence
            alt = alignment.get("vertical_distance_m", 999.0)
            vz = alignment.get("vertical_speed_mps", 999.0)
            if (
                alt <= self.config.confirmation.max_touchdown_altitude_m
                and vz <= self.config.confirmation.max_touchdown_velocity_mps
            ):
                self._persistence_frame_count += 1
                if self._persistence_frame_count >= self.config.confirmation.required_persistence_frames:
                    return LandingPhase.LANDING_CONFIRMED
            else:
                self._persistence_frame_count = 0

        elif self._current_phase == LandingPhase.ABORTING:
            # Abort transitions to RECOVERY
            return LandingPhase.RECOVERY

        elif self._current_phase == LandingPhase.RECOVERY:
            # Once recovered and target re-acquired, transition to SEARCHING or TARGET_ACQUIRED
            if context.pose_result is not None and context.pose_result.is_valid:
                return LandingPhase.TARGET_ACQUIRED
            return LandingPhase.SEARCHING

        return self._current_phase

    def _transition_to(self, target_phase: LandingPhase, timestamp_sec: float) -> None:
        """Executes validated state transition and resets phase duration timers."""
        valid_targets = VALID_TRANSITIONS.get(self._current_phase, set())
        if target_phase != self._current_phase and target_phase not in valid_targets:
            raise InvalidStateTransitionError(
                f"Illegal landing state transition from '{self._current_phase.value}' to '{target_phase.value}'"
            )

        logger.info("Landing Phase Transition: %s -> %s", self._current_phase.value, target_phase.value)
        self._previous_phase = self._current_phase
        self._current_phase = target_phase
        self._phase_start_time_sec = timestamp_sec
        self._persistence_frame_count = 0

    def _check_state_timeout(self, duration_sec: float) -> tuple:
        """Checks whether the current phase has exceeded its configured maximum duration."""
        cfg = self.config.timeouts
        timeout_limit = None

        if self._current_phase == LandingPhase.SEARCHING:
            timeout_limit = cfg.search_timeout_sec
        elif self._current_phase == LandingPhase.ALIGNING:
            timeout_limit = cfg.alignment_timeout_sec
        elif self._current_phase == LandingPhase.APPROACHING:
            timeout_limit = cfg.approach_timeout_sec
        elif self._current_phase == LandingPhase.DESCENDING:
            timeout_limit = cfg.descent_timeout_sec
        elif self._current_phase == LandingPhase.RECOVERY:
            timeout_limit = cfg.recovery_timeout_sec

        if timeout_limit is not None and duration_sec > timeout_limit:
            return True, SafetyReasonCode.STATE_TIMEOUT

        return False, SafetyReasonCode.NONE

    def _build_decision(
        self,
        context: LandingSafetyContext,
        phase: LandingPhase,
        action: RecommendedAction,
        primary_reason: SafetyReasonCode,
        reasons: List[SafetyReasonCode],
        is_safe: bool,
        confidence: float,
        metadata: Optional[dict] = None,
    ) -> LandingDecision:
        """Constructs a fully explainable LandingDecision schema."""
        meta = metadata or {}
        target_id = context.pose_result.target_id if context.pose_result is not None else None

        return LandingDecision(
            timestamp_sec=context.timestamp_sec,
            current_state=phase,
            previous_state=self._previous_phase,
            recommended_action=action,
            decision_code=f"DEC_{self._decision_sequence_id:06d}_{phase.value}_{action.value}",
            primary_reason=primary_reason,
            reason_codes=reasons if reasons else [primary_reason],
            target_id=target_id,
            estimator_health=meta.get("estimator_health", EstimatorHealthStatus.UNINITIALIZED),
            target_health=meta.get("target_health", TargetHealthStatus.UNINITIALIZED),
            is_safe_for_progression=is_safe,
            confidence=confidence,
            uncertainty_metrics=meta.get("uncertainty", {}),
            alignment_metrics=meta.get("alignment", {}),
            diagnostics={
                "sequence_id": self._decision_sequence_id,
                "phase_duration_sec": context.timestamp_sec - self._phase_start_time_sec,
                "persistence_frames": self._persistence_frame_count,
            },
        )
