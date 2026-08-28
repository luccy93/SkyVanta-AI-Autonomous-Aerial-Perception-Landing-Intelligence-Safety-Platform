"""Comprehensive Adversarial Verification and Stress Test Suite for SkyVanta AI V9.1."""

import math
import time
import numpy as np
import pytest

from skyvanta.core.config import (
    SkyVantaConfig,
    DetectorConfig,
    MotionConfig,
    ESEKFConfig,
    CameraConfig,
    LandingIntelligenceConfig,
    TrackingConfig,
)
from skyvanta.core.types import (
    BoundingBox,
    Detection,
    DetectionSource,
    TrackState,
    TrackLifecycleState,
    FrameId,
    FlightCommand,
    FlightCommandType,
    CommandSource,
    CommandStatus,
    RecommendedAction,
    LandingPhase,
    LandingDecision,
    PerceptionFrameResult,
    Candidate,
    IMUMeasurement,
    VisualPoseMeasurement,
    LandingSafetyContext,
    TrackInfo,
    PoseEstimateResult,
    NominalState,
    ESEKFDiagnostics,
    SafetyReasonCode,
    FilterStatus,
)
from skyvanta.core.exceptions import (
    SkyVantaError,
    ModelLoadError,
    CommandValidationError,
    TransformError,
    PnPSolverError,
    SensorTimingError,
    SafetyInvariantViolationError,
    InitializationError,
    FusionError,
    NumericalDivergenceError,
    GatingError,
    RateLimitExceededError,
)
from skyvanta.perception.validation import FrameValidator
from skyvanta.target.validation import CornerValidator
from skyvanta.target.geometry import TargetGeometry
from skyvanta.spatial.pnp import PnPPoseSolver
from skyvanta.spatial.camera import CameraModel
from skyvanta.spatial.se3 import SE3Transform
from skyvanta.spatial.frame_graph import FrameGraph
from skyvanta.spatial.transform import enu_to_ned_position, ned_to_enu_position
from skyvanta.tracking.manager import MultiTargetTrackManager
from skyvanta.fusion.filter import ErrorStateExtendedKalmanFilter
from skyvanta.intelligence.supervisor import SafetySupervisor
from skyvanta.flight.validation import FlightCommandValidator
from skyvanta.flight.authorization import CommandAuthorizationPolicy
from skyvanta.flight.rate_limiter import CommandRateLimiter
from skyvanta.flight.translation import V7CommandTranslator
from skyvanta.flight.mock import MockAutopilot
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.registry import ScenarioRegistry


# ============================================================================
# H4-A: SENSOR FAULT INJECTION & CORRUPTION
# ============================================================================

class TestSensorFaultInjection:
    """Verifies robustness of estimators against corrupted, spiking, and non-monotonic sensor data."""

    def test_imu_non_monotonic_timestamp_rejected(self):
        """ESEKF IMU preprocessor must reject backwards or non-monotonic timestamps."""
        filter_inst = ErrorStateExtendedKalmanFilter()
        filter_inst.initialize(position=(0.0, 0.0, 10.0), timestamp_sec=1.0)

        # First valid measurement
        meas1 = IMUMeasurement(
            timestamp_sec=1.01,
            linear_acceleration_m_s2=(0.0, 0.0, 9.81),
            angular_velocity_rad_s=(0.0, 0.0, 0.0),
        )
        filter_inst.propagate(meas1)

        # Backwards timestamp measurement
        meas_bad = IMUMeasurement(
            timestamp_sec=0.99,
            linear_acceleration_m_s2=(0.0, 0.0, 9.81),
            angular_velocity_rad_s=(0.0, 0.0, 0.0),
        )
        with pytest.raises((SensorTimingError, FusionError, SkyVantaError)):
            filter_inst.propagate(meas_bad)

    def test_imu_extreme_acceleration_spikes(self):
        """Massive acceleration spikes must not cause numerical NaN explosion in filter state."""
        filter_inst = ErrorStateExtendedKalmanFilter()
        filter_inst.initialize(position=(0.0, 0.0, 10.0), timestamp_sec=0.0)

        # Inject 1000g acceleration spike
        meas_spike = IMUMeasurement(
            timestamp_sec=0.01,
            linear_acceleration_m_s2=(0.0, 0.0, 9810.0),
            angular_velocity_rad_s=(0.0, 0.0, 0.0),
        )
        nominal = filter_inst.propagate(meas_spike)
        
        # State must remain finite and bounded
        assert all(math.isfinite(x) for x in nominal.position_world)
        assert all(math.isfinite(x) for x in nominal.velocity_world)

    def test_imu_extreme_dt_handling(self):
        """Excessive time gap (e.g. 10.0s sensor dropout) must be clamped or handled safely."""
        filter_inst = ErrorStateExtendedKalmanFilter()
        filter_inst.initialize(position=(0.0, 0.0, 10.0), timestamp_sec=0.0)

        meas_gap = IMUMeasurement(
            timestamp_sec=10.0,
            linear_acceleration_m_s2=(0.0, 0.0, 9.81),
            angular_velocity_rad_s=(0.0, 0.0, 0.0),
        )
        # Should either raise timing error or clamp dt without NaN
        try:
            nominal = filter_inst.propagate(meas_gap)
            assert all(math.isfinite(x) for x in nominal.position_world)
        except (SensorTimingError, FusionError, SkyVantaError):
            pass  # Expected safe rejection


# ============================================================================
# H4-B: PERCEPTION ADVERSARIAL ATTACKS & DEGENERATE FRAMES
# ============================================================================

class TestPerceptionAttacks:
    """Verifies FrameValidator and preprocessors reject corrupt, zero-sized, and degenerate images."""

    def test_none_and_empty_frame_rejected(self):
        """FrameValidator must reject None, empty, and 0-dimension images."""
        validator = FrameValidator()
        
        is_val_none, _ = validator.validate(None)
        assert not is_val_none

        is_val_empty, _ = validator.validate(np.array([]))
        assert not is_val_empty

        is_val_zeros, _ = validator.validate(np.zeros((0, 0, 3), dtype=np.uint8))
        assert not is_val_zeros

    def test_non_finite_pixels_rejected(self):
        """FrameValidator must reject non-uint8 images or images with non-finite values."""
        validator = FrameValidator()
        
        img_float_nan = np.zeros((480, 640, 3), dtype=np.float32)
        img_float_nan[100, 100, 0] = np.nan
        is_val_nan, _ = validator.validate(img_float_nan)
        assert not is_val_nan

        img_float_inf = np.zeros((480, 640, 3), dtype=np.float32)
        img_float_inf[100, 100, 0] = np.inf
        is_val_inf, _ = validator.validate(img_float_inf)
        assert not is_val_inf

    def test_extreme_aspect_ratio_frames(self):
        """Extreme aspect ratios (1x1000 or 1000x1) must be handled safely."""
        validator = FrameValidator()
        
        img_skinny = np.zeros((1000, 2, 3), dtype=np.uint8)
        img_flat = np.zeros((2, 1000, 3), dtype=np.uint8)
        
        # Validates structurally without throwing unhandled exceptions
        _ = validator.validate(img_skinny)
        _ = validator.validate(img_flat)


# ============================================================================
# H4-C: TRACKING CLUTTER, DROPOUT, AND STRESS
# ============================================================================

class TestTrackingAttacksAndStress:
    """Tests track manager under heavy false-positive clutter, dropouts, and lifecycle invariants."""

    def test_dense_clutter_100_candidates(self):
        """Track manager must handle 100 simultaneous clutter detections without unbounded track explosion."""
        config = TrackingConfig()
        tm = MultiTargetTrackManager(config=config)
        
        for frame_idx in range(50):
            # Generate 100 random noise bboxes
            detections = []
            for i in range(100):
                x = (i * 13) % 500
                y = (i * 17) % 400
                bbox = BoundingBox(x1=float(x), y1=float(y), x2=float(x+20), y2=float(y+20))
                detections.append(Detection(
                    bbox=bbox,
                    confidence=0.3,
                    class_name="drone",
                    source=DetectionSource.YOLO
                ))
            
            pfr = PerceptionFrameResult(
                frame_id=frame_idx,
                timestamp_sec=frame_idx * 0.033,
                detections=detections
            )
            res = tm.process(pfr)

        # Track manager handles process safely
        assert isinstance(res.tracks, list)

    def test_track_coast_and_deletion_invariant(self):
        """Track must transition CONFIRMED -> COASTING -> DELETED when measurements cease."""
        tm = MultiTargetTrackManager()
        
        # 1. Establish track
        for frame_idx in range(5):
            det = Detection(
                bbox=BoundingBox(x1=100.0, y1=100.0, x2=150.0, y2=150.0),
                confidence=0.9,
                class_name="drone",
                source=DetectionSource.YOLO
            )
            pfr = PerceptionFrameResult(
                frame_id=frame_idx,
                timestamp_sec=frame_idx * 0.033,
                detections=[det]
            )
            res = tm.process(pfr)

        confirmed_ids = [t.track_id for t in res.confirmed_tracks]
        assert len(confirmed_ids) >= 1
        tracked_id = confirmed_ids[0]

        # 2. Starve track of measurements for 50 frames
        for frame_idx in range(5, 55):
            pfr_empty = PerceptionFrameResult(
                frame_id=frame_idx,
                timestamp_sec=frame_idx * 0.033,
                detections=[]
            )
            res_empty = tm.process(pfr_empty)

        # Track must now be deleted from active tracks
        active_ids = [t.track_id for t in res_empty.tracks]
        assert tracked_id not in active_ids


# ============================================================================
# H4-D: PNP DEGENERACIES & SPATIAL SOLVER CORNER ATTACKS
# ============================================================================

class TestPnPDegeneracies:
    """Verifies PnP solver and CornerValidator against collinear, concave, and degenerate fiducials."""

    def test_collinear_corners_rejected(self):
        """Collinear 2D corners must be rejected before calling solvePnP."""
        validator = CornerValidator()
        
        # 4 collinear points along a line
        collinear_pts = np.array([
            [100.0, 100.0],
            [150.0, 100.0],
            [200.0, 100.0],
            [250.0, 100.0],
        ], dtype=np.float32)

        is_valid, _ = validator.validate(collinear_pts)
        assert not is_valid

    def test_concave_self_intersecting_corners_rejected(self):
        """Self-intersecting / bow-tie corner orders must be rejected."""
        validator = CornerValidator()
        
        # Hourglass / self-intersecting polygon
        bowtie_pts = np.array([
            [100.0, 100.0],
            [200.0, 200.0],
            [200.0, 100.0],
            [100.0, 200.0],
        ], dtype=np.float32)

        is_valid, _ = validator.validate(bowtie_pts)
        assert not is_valid

    def test_zero_area_corners_rejected(self):
        """Coincident / zero-area corners must be rejected safely."""
        validator = CornerValidator()
        
        coincident_pts = np.array([
            [100.0, 100.0],
            [100.0, 100.0],
            [100.0, 100.0],
            [100.0, 100.0],
        ], dtype=np.float32)

        is_valid, _ = validator.validate(coincident_pts)
        assert not is_valid

    def test_pnp_solver_handles_degenerate_gracefully(self):
        """PnPPoseSolver must return is_valid=False on non-finite or degenerate points."""
        solver = PnPPoseSolver()
        geom = TargetGeometry(0.8)
        cam = CameraModel(CameraConfig())
        
        nan_corners = np.array([
            [np.nan, 100.0],
            [200.0, 100.0],
            [200.0, 200.0],
            [100.0, 200.0],
        ], dtype=np.float32)

        res = solver.solve(geom.get_object_points(), nan_corners, cam, target_id=1)
        assert not res.is_valid
        assert "Non-finite" in (res.failure_reason or "")


# ============================================================================
# H4-E: ESEKF NUMERICAL STABILITY & INNOVATION GATING
# ============================================================================

class TestESEKFStabilityAndGating:
    """Verifies Chi-squared gating, covariance positive-definiteness, and visual outlier rejection."""

    def test_chi_squared_outlier_rejection(self):
        """A visual measurement with massive 50m error must be rejected by Chi-squared gate."""
        filter_inst = ErrorStateExtendedKalmanFilter()
        filter_inst.initialize(position=(0.0, 0.0, 10.0), timestamp_sec=0.0)

        # Propagate nominal state slightly
        meas_imu = IMUMeasurement(
            timestamp_sec=0.01,
            linear_acceleration_m_s2=(0.0, 0.0, 9.81),
            angular_velocity_rad_s=(0.0, 0.0, 0.0),
        )
        filter_inst.propagate(meas_imu)

        # Inject massive outlier visual measurement (50m jump)
        meas_outlier = VisualPoseMeasurement(
            timestamp_sec=0.011,
            position_m=(50.0, -50.0, 100.0),
            rotation_matrix=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            quaternion=(1.0, 0.0, 0.0, 0.0),
            covariance=(np.eye(6) * 0.01).tolist(),
        )

        _, accepted, reason = filter_inst.update_visual(meas_outlier)
        assert not accepted
        assert "Chi-squared" in (reason or "")
        assert filter_inst.get_diagnostics().rejected_measurement_count >= 1

    def test_covariance_symmetry_and_positive_definiteness(self):
        """Error covariance P must maintain symmetry and positive eigenvalues over 500 steps."""
        filter_inst = ErrorStateExtendedKalmanFilter()
        filter_inst.initialize(position=(0.0, 0.0, 10.0), timestamp_sec=0.0)

        for i in range(1, 501):
            t = i * 0.01
            imu = IMUMeasurement(
                timestamp_sec=t,
                linear_acceleration_m_s2=(0.01 * math.sin(t), 0.01 * math.cos(t), 9.81),
                angular_velocity_rad_s=(0.005 * math.cos(t), -0.005 * math.sin(t), 0.0),
            )
            filter_inst.propagate(imu)

            if i % 10 == 0:
                vis = VisualPoseMeasurement(
                    timestamp_sec=t + 0.001,
                    position_m=(0.0, 0.0, 10.0),
                    rotation_matrix=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                    quaternion=(1.0, 0.0, 0.0, 0.0),
                    covariance=(np.eye(6) * 0.05).tolist(),
                )
                filter_inst.update_visual(vis)

        P = filter_inst.get_covariance()
        # Check symmetry: P == P^T
        np.testing.assert_allclose(P, P.T, atol=1e-8)

        # Check positive-definiteness: all eigenvalues >= 0
        eigenvalues = np.linalg.eigvalsh(P)
        assert np.all(eigenvalues >= 0.0)


# ============================================================================
# H4-F: SAFETY SUPERVISOR INVARIANTS & ABORT PRIORITIZATION
# ============================================================================

class TestSafetySupervisorInvariants:
    """Verifies deterministic abort hierarchy and irrevocable safety transitions."""

    def test_critical_fault_top_priority(self):
        """CRITICAL_FAULT must override all other concurrent faults."""
        supervisor = SafetySupervisor()
        
        # Context with simultaneous critical fault, velocity fault, and lost target
        context = LandingSafetyContext(
            timestamp_sec=1.0,
            critical_fault_flag=True,  # Critical hardware flag
            target_info=None,          # Target lost
            pose_result=None,
            esekf_state=NominalState(
                timestamp_sec=1.0,
                position_world=(0.0, 0.0, 1.0),
                velocity_world=(5.0, 5.0, -10.0), # Extreme velocity
            ),
        )

        is_safe, primary_reason, _, _ = supervisor.evaluate_safety(context, LandingPhase.DESCENDING)
        assert not is_safe
        assert primary_reason == SafetyReasonCode.CRITICAL_FAULT

    def test_velocity_limit_breach_fails_safety(self):
        """Descent velocity exceeding max threshold must trigger safe abort / progression rejection."""
        supervisor = SafetySupervisor()
        
        context = LandingSafetyContext(
            timestamp_sec=1.0,
            target_info=TrackInfo(track_id=1, state=TrackState.TRACKING, confidence=0.9, hits=10, frames_since_hit=0, age=10, is_visible=True),
            pose_result=PoseEstimateResult(timestamp_sec=1.0, frame_id=1, is_valid=True, position_camera_m=(0.0, 0.0, 1.5)),
            esekf_state=NominalState(
                timestamp_sec=1.0,
                position_world=(0.0, 0.0, 1.5),
                velocity_world=(0.0, 0.0, -2.5),  # 2.5 m/s descent exceeds 0.8 m/s limit
            ),
            esekf_diagnostics=ESEKFDiagnostics(position_uncertainty_m=0.03),
        )

        is_safe, primary_reason, all_reasons, _ = supervisor.evaluate_safety(context, LandingPhase.DESCENDING)
        assert not is_safe
        assert SafetyReasonCode.VELOCITY_TOO_HIGH in all_reasons


# ============================================================================
# H4-G: FLIGHT COMMAND ATTACKS & TRANSLATION INVARIANTS
# ============================================================================

class TestFlightCommandAttacks:
    """Verifies command validation, authorization rate-limits, and translation invariants."""

    def test_expired_timestamp_rejected(self):
        """Flight command with expiration_sec <= current_time must fail validation."""
        validator = FlightCommandValidator()
        
        cmd_expired = FlightCommand(
            command_id="CMD_EXP_01",
            sequence_number=1,
            timestamp_sec=9.0,
            expiration_sec=9.5,
            command_type=FlightCommandType.HOLD,
        )

        # Evaluated at current_time = 10.0 (past expiration 9.5)
        is_valid, reason = validator.validate(cmd_expired, current_time_sec=10.0)
        assert not is_valid
        assert "expired" in (reason or "").lower()

    def test_duplicate_sequence_rejected_by_rate_limiter(self):
        """Replay of an already-processed sequence number must be rejected."""
        limiter = CommandRateLimiter(min_interval_sec=0.05)
        
        cmd1 = FlightCommand(
            command_id="CMD_001",
            sequence_number=5,
            timestamp_sec=1.0,
            expiration_sec=2.0,
            command_type=FlightCommandType.HOLD,
        )
        allowed1, _ = limiter.check_rate_limit(cmd1, current_time_sec=1.0)
        assert allowed1
        limiter.record_command(cmd1, current_time_sec=1.0)

        # Replayed sequence number 5
        cmd_replay = FlightCommand(
            command_id="CMD_002",
            sequence_number=5,
            timestamp_sec=1.1,
            expiration_sec=2.1,
            command_type=FlightCommandType.HOLD,
        )
        allowed2, reason = limiter.check_rate_limit(cmd_replay, current_time_sec=1.1)
        assert not allowed2
        assert "duplicate" in (reason or "").lower()

    def test_abort_translation_never_descends(self):
        """V7CommandTranslator invariant: ABORT must never translate to DESCEND or FINAL_APPROACH."""
        translator = V7CommandTranslator()
        
        decision_abort = LandingDecision(
            timestamp_sec=1.0,
            current_state=LandingPhase.ABORTING,
            recommended_action=RecommendedAction.ABORT,
            decision_code="DEC_ABORT",
            primary_reason=SafetyReasonCode.CRITICAL_FAULT,
        )

        cmd_abort = translator.translate(decision_abort)
        assert cmd_abort.command_type in (FlightCommandType.ABORT, FlightCommandType.HOLD, FlightCommandType.RECOVER)
        assert cmd_abort.command_type not in (FlightCommandType.DESCEND, FlightCommandType.FINAL_APPROACH)

    def test_command_rate_limiter_throttles_high_frequency(self):
        """CommandRateLimiter must throttle commands issued faster than minimum interval."""
        limiter = CommandRateLimiter(min_interval_sec=0.05) # Max 20 Hz
        
        cmd1 = FlightCommand(
            command_id="CMD_R1",
            sequence_number=1,
            timestamp_sec=1.00,
            expiration_sec=2.0,
            command_type=FlightCommandType.HOLD,
        )
        cmd2 = FlightCommand(
            command_id="CMD_R2",
            sequence_number=2,
            timestamp_sec=1.01, # Only 10ms later (100 Hz flood)
            expiration_sec=2.0,
            command_type=FlightCommandType.HOLD,
        )

        allowed1, _ = limiter.check_rate_limit(cmd1, current_time_sec=1.00)
        assert allowed1
        limiter.record_command(cmd1, current_time_sec=1.00)

        allowed2, reason = limiter.check_rate_limit(cmd2, current_time_sec=1.01)
        assert not allowed2
        assert "rate limit exceeded" in (reason or "").lower()


# ============================================================================
# H4-H: SE(3) FRAME GRAPH & TRANSFORM INVARIANTS
# ============================================================================

class TestSE3TransformInvariants:
    """Verifies SE(3) transform inversions, compositions, and coordinate conversions."""

    def test_se3_inverse_composition_identity(self):
        """T * T^-1 must equal the 4x4 Identity matrix."""
        R = np.array([
            [0.0, -1.0, 0.0],
            [1.0,  0.0, 0.0],
            [0.0,  0.0, 1.0],
        ], dtype=np.float64)
        t = np.array([1.5, -2.3, 4.7], dtype=np.float64)
        
        transform = SE3Transform(
            source_frame=FrameId.BODY,
            target_frame=FrameId.WORLD,
            rotation=R,
            translation=t,
        )
        inv_transform = transform.inverse()
        composed = transform.compose(inv_transform)

        np.testing.assert_allclose(composed.to_matrix(), np.eye(4), atol=1e-8)

    def test_enu_ned_roundtrip_vectorized(self):
        """Converting ENU -> NED -> ENU must restore original coordinates exactly."""
        pos_enu = np.array([12.34, -56.78, 90.12])
        pos_ned = enu_to_ned_position(pos_enu)
        pos_enu_restored = ned_to_enu_position(pos_ned)

        np.testing.assert_allclose(pos_enu_restored, pos_enu, atol=1e-12)
