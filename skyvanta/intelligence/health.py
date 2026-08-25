"""Subsystem health evaluators and geometric alignment calculations."""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from skyvanta.core.config import LandingIntelligenceConfig
from skyvanta.core.types import (
    EstimatorHealthStatus,
    FilterStatus,
    LandingSafetyContext,
    SafetyReasonCode,
    TargetHealthStatus,
)


def evaluate_estimator_health(
    context: LandingSafetyContext,
    config: LandingIntelligenceConfig,
) -> Tuple[EstimatorHealthStatus, List[SafetyReasonCode]]:
    """Evaluates the operational health and staleness of the ESEKF state estimator."""
    reasons: List[SafetyReasonCode] = []

    if context.esekf_state is None:
        reasons.append(SafetyReasonCode.ESTIMATOR_UNINITIALIZED)
        return EstimatorHealthStatus.UNINITIALIZED, reasons

    state = context.esekf_state
    if state.status == FilterStatus.UNINITIALIZED:
        reasons.append(SafetyReasonCode.ESTIMATOR_UNINITIALIZED)
        return EstimatorHealthStatus.UNINITIALIZED, reasons

    # Staleness check
    age_sec = abs(context.timestamp_sec - state.timestamp_sec)
    if age_sec > config.freshness.max_estimator_age_sec:
        reasons.append(SafetyReasonCode.ESTIMATOR_STALE)
        return EstimatorHealthStatus.STALE, reasons

    # Diagnostics check if present
    if context.esekf_diagnostics is not None:
        diag = context.esekf_diagnostics
        if diag.position_uncertainty_m > config.uncertainty.max_position_3sigma_m:
            reasons.append(SafetyReasonCode.POSITION_UNCERTAINTY_HIGH)
        if diag.velocity_uncertainty_m_s > config.uncertainty.max_velocity_3sigma_mps:
            reasons.append(SafetyReasonCode.VELOCITY_UNCERTAINTY_HIGH)
        if diag.orientation_uncertainty_deg > config.uncertainty.max_orientation_3sigma_deg:
            reasons.append(SafetyReasonCode.ORIENTATION_UNCERTAINTY_HIGH)

    if reasons:
        return EstimatorHealthStatus.DEGRADED, reasons

    return EstimatorHealthStatus.HEALTHY, []


def evaluate_target_health(
    context: LandingSafetyContext,
    config: LandingIntelligenceConfig,
) -> Tuple[TargetHealthStatus, List[SafetyReasonCode]]:
    """Evaluates the validity, continuity, and freshness of the perceived landing target."""
    reasons: List[SafetyReasonCode] = []

    if context.pose_result is None or not context.pose_result.is_valid or context.pose_result.pose is None:
        reasons.append(SafetyReasonCode.TARGET_NOT_FOUND)
        return TargetHealthStatus.LOST, reasons

    pose = context.pose_result.pose
    age_sec = abs(context.timestamp_sec - pose.timestamp_sec)

    if age_sec > config.freshness.max_pose_age_sec:
        reasons.append(SafetyReasonCode.POSE_STALE)
        return TargetHealthStatus.STALE, reasons

    if pose.pose_quality < 0.2:
        reasons.append(SafetyReasonCode.POSE_INVALID)

    if pose.reprojection_error_rms > 5.0:
        reasons.append(SafetyReasonCode.REPROJECTION_ERROR_HIGH)

    if context.target_info is not None and not context.target_info.is_valid:
        reasons.append(SafetyReasonCode.TRACK_UNSTABLE)

    if reasons:
        return TargetHealthStatus.DEGRADED, reasons

    return TargetHealthStatus.HEALTHY, []


def calculate_alignment_metrics(context: LandingSafetyContext) -> Dict[str, float]:
    """Extracts metric body-relative or pad-relative translation and orientation offsets."""
    metrics: Dict[str, float] = {
        "lateral_error_m": 0.0,
        "longitudinal_error_m": 0.0,
        "vertical_distance_m": 0.0,
        "horizontal_distance_m": 0.0,
        "yaw_error_deg": 0.0,
        "horizontal_speed_mps": 0.0,
        "vertical_speed_mps": 0.0,
    }

    # 1. Geometry from 6-DoF pose (prefer body-relative spatial localization if available)
    pose = None
    if context.spatial_localization is not None and context.spatial_localization.is_valid:
        pose = context.spatial_localization.pose
    elif context.pose_result is not None and context.pose_result.is_valid:
        pose = context.pose_result.pose

    if pose is not None:
        # In Camera/Body frame: X is right (lateral), Y is down/longitudinal, Z is depth/range
        dx = abs(pose.x)
        dy = abs(pose.y)
        dz = abs(pose.z)

        metrics["lateral_error_m"] = float(dx)
        metrics["longitudinal_error_m"] = float(dy)
        metrics["vertical_distance_m"] = float(dz)
        metrics["horizontal_distance_m"] = float(math.sqrt(dx ** 2 + dy ** 2))
        metrics["yaw_error_deg"] = float(abs(pose.euler_deg[2]))


    # 2. Kinematic velocity from ESEKF
    if context.esekf_state is not None:
        vx, vy, vz = context.esekf_state.velocity_world
        metrics["horizontal_speed_mps"] = float(math.sqrt(vx ** 2 + vy ** 2))
        metrics["vertical_speed_mps"] = float(abs(vz))

    return metrics


def extract_uncertainty_metrics(
    context: LandingSafetyContext,
    config: LandingIntelligenceConfig,
) -> Dict[str, float]:
    """Extracts 3-sigma estimation uncertainties."""
    metrics = {
        "position_3sigma_m": 0.0,
        "velocity_3sigma_mps": 0.0,
        "orientation_3sigma_deg": 0.0,
    }

    if context.esekf_diagnostics is not None:
        metrics["position_3sigma_m"] = context.esekf_diagnostics.position_uncertainty_m
        metrics["velocity_3sigma_mps"] = context.esekf_diagnostics.velocity_uncertainty_m_s
        metrics["orientation_3sigma_deg"] = context.esekf_diagnostics.orientation_uncertainty_deg

    return metrics
