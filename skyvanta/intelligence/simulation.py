"""Deterministic scenario generation and automated test harness for Landing Intelligence."""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from skyvanta.core.config import LandingIntelligenceConfig
from skyvanta.core.types import (
    ESEKFDiagnostics,
    FilterStatus,
    FrameId,
    LandingDecision,
    LandingPhase,
    LandingSafetyContext,
    NominalState,
    Pose6D,
    PoseEstimateResult,
    RecommendedAction,
    TrackInfo,
)
from skyvanta.intelligence.fsm import LandingStateMachine


class LandingScenarioSimulator:
    """Runs deterministic landing progression and safety stress scenarios."""

    @staticmethod
    def create_context(
        timestamp_sec: float,
        target_pos_body: Optional[Tuple[float, float, float]] = (0.0, 0.0, 5.0),
        target_yaw_deg: float = 0.0,
        drone_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        position_3sigma_m: float = 0.05,
        target_valid: bool = True,
        reprojection_error: float = 0.5,
        critical_fault: bool = False,
    ) -> LandingSafetyContext:
        """Helper to create a fully specified synthetic LandingSafetyContext."""
        pose_res = None
        if target_valid and target_pos_body is not None:
            tx, ty, tz = target_pos_body
            range_m = float(np.linalg.norm([tx, ty, tz]))
            pose_6d = Pose6D(
                x=float(tx),
                y=float(ty),
                z=float(tz),
                range_m=range_m,
                rotation_matrix=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                rvec=(0.0, 0.0, float(np.radians(target_yaw_deg))),
                quaternion=(1.0, 0.0, 0.0, 0.0),
                euler_deg=(0.0, 0.0, float(target_yaw_deg)),
                euler_rad=(0.0, 0.0, float(np.radians(target_yaw_deg))),
                reprojection_error_rms=reprojection_error,
                reprojection_error_max=reprojection_error * 1.5,
                pose_quality=1.0,
                is_valid=True,
                timestamp_sec=timestamp_sec,
                frame_id=0,
                target_id=1,
            )
            pose_res = PoseEstimateResult(
                timestamp_sec=timestamp_sec,
                frame_id=0,
                target_id=1,
                pose=pose_6d,
                reprojection_error_rms=reprojection_error,
                pose_quality=1.0,
                is_valid=True,
            )


        esekf_state = NominalState(
            timestamp_sec=timestamp_sec,
            position_world=(0.0, 0.0, -10.0),
            velocity_world=drone_velocity,
            rotation_matrix=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            status=FilterStatus.INITIALIZED,
        )

        esekf_diag = ESEKFDiagnostics(
            propagation_count=100,
            visual_update_count=20,
            position_uncertainty_m=position_3sigma_m,
            velocity_uncertainty_m_s=0.05,
            orientation_uncertainty_deg=0.5,
        )

        return LandingSafetyContext(
            timestamp_sec=timestamp_sec,
            pose_result=pose_res,
            esekf_state=esekf_state,
            esekf_diagnostics=esekf_diag,
            critical_fault_flag=critical_fault,
        )
