"""Safety supervisor enforcing independent invariants and deterministic abort prioritization."""

from typing import Any, Dict, List, Optional, Tuple

from skyvanta.core.config import LandingIntelligenceConfig
from skyvanta.core.types import (
    EstimatorHealthStatus,
    LandingPhase,
    LandingSafetyContext,
    SafetyReasonCode,
    TargetHealthStatus,
)
from skyvanta.intelligence.health import (
    calculate_alignment_metrics,
    evaluate_estimator_health,
    evaluate_target_health,
    extract_uncertainty_metrics,
)


class SafetySupervisor:
    """Evaluates multi-subsystem safety invariants and establishes deterministic priority ordering."""

    def __init__(self, config: Optional[LandingIntelligenceConfig] = None):
        self.config = config or LandingIntelligenceConfig()

    def evaluate_safety(
        self,
        context: LandingSafetyContext,
        current_phase: LandingPhase,
    ) -> Tuple[bool, SafetyReasonCode, List[SafetyReasonCode], Dict[str, Any]]:
        """Evaluates all safety invariants and determines whether the system is safe to progress.

        Returns:
            (is_safe, primary_reason, all_reasons, evaluation_metadata)
        """
        all_reasons: List[SafetyReasonCode] = []

        # 1. Check Critical Hardware/Software Fault Flag
        if context.critical_fault_flag:
            return False, SafetyReasonCode.CRITICAL_FAULT, [SafetyReasonCode.CRITICAL_FAULT], {}

        # 2. Evaluate Subsystem Health
        est_health, est_reasons = evaluate_estimator_health(context, self.config)
        tgt_health, tgt_reasons = evaluate_target_health(context, self.config)
        all_reasons.extend(est_reasons)
        all_reasons.extend(tgt_reasons)

        alignment = calculate_alignment_metrics(context)
        uncertainty = extract_uncertainty_metrics(context, self.config)

        # 3. Kinematic Velocity Checks
        if alignment["horizontal_speed_mps"] > self.config.velocity.max_horizontal_speed_mps:
            all_reasons.append(SafetyReasonCode.VELOCITY_TOO_HIGH)
        if alignment["vertical_speed_mps"] > self.config.velocity.max_descent_speed_mps:
            all_reasons.append(SafetyReasonCode.VELOCITY_TOO_HIGH)

        # 4. Phase-Specific Geometry & Uncertainty Checks
        if current_phase in (LandingPhase.ALIGNING, LandingPhase.APPROACHING):
            if alignment["lateral_error_m"] > self.config.alignment.max_lateral_error_m:
                all_reasons.append(SafetyReasonCode.LATERAL_ERROR_TOO_HIGH)
            if alignment["longitudinal_error_m"] > self.config.alignment.max_longitudinal_error_m:
                all_reasons.append(SafetyReasonCode.LONGITUDINAL_ERROR_TOO_HIGH)
            if alignment["yaw_error_deg"] > self.config.alignment.max_yaw_error_deg:
                all_reasons.append(SafetyReasonCode.YAW_ERROR_TOO_HIGH)

        elif current_phase in (LandingPhase.DESCENDING, LandingPhase.FINAL_APPROACH):
            if alignment["lateral_error_m"] > self.config.alignment.final_lateral_error_m:
                all_reasons.append(SafetyReasonCode.LATERAL_ERROR_TOO_HIGH)
            if alignment["yaw_error_deg"] > self.config.alignment.final_yaw_error_deg:
                all_reasons.append(SafetyReasonCode.YAW_ERROR_TOO_HIGH)
            if uncertainty["position_3sigma_m"] > self.config.uncertainty.final_position_3sigma_m:
                all_reasons.append(SafetyReasonCode.POSITION_UNCERTAINTY_HIGH)

        metadata = {
            "estimator_health": est_health,
            "target_health": tgt_health,
            "alignment": alignment,
            "uncertainty": uncertainty,
        }

        if not all_reasons:
            return True, SafetyReasonCode.NOMINAL_CONDITIONS, [], metadata

        # Deterministic Priority Selection
        primary = self._select_primary_reason(all_reasons)
        return False, primary, all_reasons, metadata

    def _select_primary_reason(self, reasons: List[SafetyReasonCode]) -> SafetyReasonCode:
        """Applies strict hierarchical safety priority ordering."""
        priority_order = [
            SafetyReasonCode.CRITICAL_FAULT,
            SafetyReasonCode.ESTIMATOR_UNINITIALIZED,
            SafetyReasonCode.ESTIMATOR_STALE,
            SafetyReasonCode.TARGET_LOST,
            SafetyReasonCode.TARGET_NOT_FOUND,
            SafetyReasonCode.POSE_STALE,
            SafetyReasonCode.POSE_INVALID,
            SafetyReasonCode.POSITION_UNCERTAINTY_HIGH,
            SafetyReasonCode.VELOCITY_UNCERTAINTY_HIGH,
            SafetyReasonCode.ORIENTATION_UNCERTAINTY_HIGH,
            SafetyReasonCode.VELOCITY_TOO_HIGH,
            SafetyReasonCode.LATERAL_ERROR_TOO_HIGH,
            SafetyReasonCode.LONGITUDINAL_ERROR_TOO_HIGH,
            SafetyReasonCode.YAW_ERROR_TOO_HIGH,
            SafetyReasonCode.STATE_TIMEOUT,
            SafetyReasonCode.REPROJECTION_ERROR_HIGH,
            SafetyReasonCode.TRACK_UNSTABLE,
        ]

        for code in priority_order:
            if code in reasons:
                return code

        return reasons[0] if reasons else SafetyReasonCode.NONE
