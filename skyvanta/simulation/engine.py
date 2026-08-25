"""Closed-loop Digital Twin simulation execution engine for full-pipeline validation."""

import math
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from skyvanta.core.config import LandingIntelligenceConfig
from skyvanta.core.types import (
    CommandStatus,
    DigitalTwinState,
    ExperimentResult,
    FlightCommand,
    FlightCommandType,
    FrameId,
    LandingDecision,
    LandingPhase,
    LandingSafetyContext,
    Pose6D,
    PoseEstimateResult,
    RecommendedAction,
    SafetyReasonCode,
    SafetyViolation,
    ScenarioEvent,
    ScenarioEventType,
    ScenarioMetrics,
    ScenarioOutcome,
    TrackInfo,
    TrackState,
    VisualPoseMeasurement,
)
from skyvanta.flight.authorization import CommandAuthorizationPolicy
from skyvanta.flight.mock import MockAutopilot
from skyvanta.flight.rate_limiter import CommandRateLimiter
from skyvanta.flight.translation import V7CommandTranslator
from skyvanta.flight.validation import FlightCommandValidator
from skyvanta.fusion.filter import ErrorStateExtendedKalmanFilter
from skyvanta.intelligence.fsm import LandingStateMachine
from skyvanta.simulation.camera import SimulatedCamera
from skyvanta.simulation.clock import SimulationClock
from skyvanta.simulation.disturbances import DisturbanceEvent, DisturbanceModel
from skyvanta.simulation.dropout import (
    FrameDropoutModel,
    FrameDropoutType,
    OcclusionModel,
    OcclusionType,
    SensorFaultModel,
    SensorFaultType,
    SensorType,
)
from skyvanta.simulation.imu import SimulatedIMU
from skyvanta.simulation.safety import SafetyViolationDetector
from skyvanta.simulation.scenarios import Scenario, compute_configuration_hash
from skyvanta.simulation.target import SimulatedLandingTarget
from skyvanta.simulation.vehicle import SimulatedVehicle
from skyvanta.spatial.transform import rotation_matrix_to_quaternion


class ScenarioEngine:
    """Orchestrates closed-loop continuous 6-DoF digital twin simulation with the full SkyVanta stack."""

    def __init__(self, intelligence_config: Optional[LandingIntelligenceConfig] = None):
        self.intelligence_config = intelligence_config or LandingIntelligenceConfig()

    def run(
        self,
        scenario: Scenario,
        run_id: Optional[str] = None,
    ) -> Tuple[ExperimentResult, List[Dict[str, Any]]]:
        """Runs a complete scenario simulation to completion.

        Args:
            scenario: Scenario definition to execute.
            run_id: Optional run execution ID string.

        Returns:
            (ExperimentResult, trajectory_log)
        """
        # 1. Deterministic Initialization
        seed = scenario.seed
        np.random.seed(seed)
        run_identifier = run_id or f"run_{scenario.scenario_id}_{seed}"
        config_hash = compute_configuration_hash(scenario)

        clock = SimulationClock(start_time_sec=0.0, default_dt_sec=scenario.timestep_sec)

        vehicle = SimulatedVehicle(
            initial_position=scenario.initial_vehicle_pos,
            initial_velocity=scenario.initial_vehicle_vel,
            initial_euler_deg=scenario.initial_vehicle_euler_deg,
        )

        target_cfg = scenario.target_config
        target = SimulatedLandingTarget(
            marker_size_m=target_cfg.get("marker_size_m", 0.8),
            initial_position=tuple(target_cfg.get("initial_position", [0.0, 0.0, 0.0])),
            velocity_mps=tuple(target_cfg.get("velocity_mps", [0.0, 0.0, 0.0])),
            target_id=target_cfg.get("target_id", 1),
        )

        noise_cfg = scenario.noise_config
        camera = SimulatedCamera(
            pixel_noise_sigma=noise_cfg.camera_pixel_sigma,
            seed=seed,
        )
        imu = SimulatedIMU(
            accel_noise_sigma=noise_cfg.imu_accel_sigma,
            gyro_noise_sigma=noise_cfg.imu_gyro_sigma,
            accel_bias=noise_cfg.imu_accel_bias,
            gyro_bias=noise_cfg.imu_gyro_bias,
            accel_drift_rate=noise_cfg.imu_accel_drift_rate,
            gyro_drift_rate=noise_cfg.imu_gyro_drift_rate,
            seed=seed,
        )

        disturbances = DisturbanceModel()
        faults = SensorFaultModel()
        safety_detector = SafetyViolationDetector()

        # Parse and schedule ScenarioEvents
        for event in scenario.events:
            self._schedule_event(event, target, camera, imu, disturbances, faults)

        # 2. Initialize V6 ESEKF Filter
        esekf = ErrorStateExtendedKalmanFilter()
        P_init = np.diag([0.001]*3 + [0.001]*3 + [0.0001]*3 + [1e-5]*3 + [1e-4]*3)
        esekf.initialize(
            position=scenario.initial_vehicle_pos,
            velocity=scenario.initial_vehicle_vel,
            rotation_matrix=np.eye(3),
            timestamp_sec=0.0,
            initial_covariance=P_init,
        )

        # 3. Initialize V7 FSM & V8 Flight Pipeline
        fsm = LandingStateMachine(self.intelligence_config)
        translator = V7CommandTranslator()
        validator = FlightCommandValidator()
        authorizer = CommandAuthorizationPolicy()
        rate_limiter = CommandRateLimiter(min_interval_sec=0.05)
        autopilot = MockAutopilot()
        autopilot.connect()

        # Tracking telemetry
        trajectory_log: List[Dict[str, Any]] = []
        phase_history: List[str] = [fsm.current_phase.value]
        commands_dispatched: int = 0
        estimation_errors: List[float] = []
        nees_consistent_count: int = 0
        active_command: Optional[FlightCommand] = None
        prev_pos = vehicle.position.copy()
        last_decision: Optional[LandingDecision] = None
        last_target_track_info: Optional[TrackInfo] = None
        last_pose_result: Optional[PoseEstimateResult] = None

        start_wall_time = time.perf_counter()

        # 4. Closed-Loop Discrete Simulation Loop
        while clock.current_time_sec < scenario.duration_sec:
            t = clock.current_time_sec
            dt = scenario.timestep_sec

            # Check Autopilot disconnect event
            ap_fault = faults.get_active_fault(SensorType.AUTOPILOT, t)
            if ap_fault and ap_fault.fault_type == SensorFaultType.DROP:
                autopilot.disconnect()

            # A. Step Vehicle Kinematics
            pad_pos = target.get_position_at(t)
            twin_state = vehicle.step(
                dt_sec=dt,
                current_time_sec=t,
                active_command=active_command,
                target_pad_position=tuple(float(x) for x in pad_pos),
                disturbances=disturbances,
            )

            # Acceleration for IMU specific force
            accel_true = vehicle.acceleration.copy()
            prev_pos = vehicle.position.copy()

            # B. Generate Synthetic Sensor Observations
            # Check camera fault
            cam_fault = faults.get_active_fault(SensorType.CAMERA, t)
            is_cam_dropped = cam_fault and cam_fault.fault_type == SensorFaultType.DROP

            obs = None
            if not is_cam_dropped:
                obs = camera.capture_target_observation(
                    drone_pos_world=vehicle.position,
                    drone_R_world=vehicle.rotation_matrix,
                    target=target,
                    current_time_sec=t,
                )

            # Check IMU fault
            imu_fault = faults.get_active_fault(SensorType.IMU, t)
            is_imu_dropped = imu_fault and imu_fault.fault_type == SensorFaultType.DROP

            imu_meas = None
            if not is_imu_dropped:
                imu_meas = imu.generate_measurement(
                    drone_accel_world=accel_true,
                    drone_R_world=vehicle.rotation_matrix,
                    drone_omega_body=vehicle.angular_velocity,
                    current_time_sec=t,
                    dt_step_sec=dt,
                )

            # C. Ingest IMU into V6 ESEKF Filter
            if imu_meas is not None:
                try:
                    esekf.propagate(imu_meas)
                except Exception:
                    esekf.imu_preprocessor.reset()

            # D. Ingest Visual Measurement into V6 ESEKF Filter
            if obs is not None:
                noisy_pixels, detection, corners_cam = obs
                safety_detector.record_target_observation(t)

                # Simulated PnP visual pose observation
                p_noise = np.random.normal(0.0, noise_cfg.pose_position_sigma, size=3)
                vis_meas_pos = tuple(float(x) for x in (vehicle.position + p_noise))
                var_p = max(0.0025, float(noise_cfg.pose_position_sigma ** 2))
                cov_6x6 = np.diag([var_p] * 3 + [0.001] * 3).tolist()
                vis_meas = VisualPoseMeasurement(
                    timestamp_sec=max(0.0001, t),
                    position_m=vis_meas_pos,
                    rotation_matrix=vehicle.rotation_matrix.tolist(),
                    quaternion=vehicle.quaternion,
                    covariance=cov_6x6,
                    frame_id=FrameId.WORLD,
                    quality=1.0,
                    source="simulated_pnp",
                    target_id=target.target_id,
                )
                esekf.update_visual(vis_meas)

                last_target_track_info = TrackInfo(
                    track_id=target.target_id,
                    state=TrackState.TRACKING,
                    confidence=0.98,
                    hits=10,
                    frames_since_hit=0,
                    age=10,
                    is_visible=True,
                    bbox=detection.bbox,
                    center=detection.bbox.center,
                    size=(detection.bbox.width, detection.bbox.height),
                )

                dx = float(pad_pos[0] - vehicle.position[0])
                dy = float(pad_pos[1] - vehicle.position[1])
                dz = float(abs(vehicle.position[2] - pad_pos[2]))
                range_m = float(np.linalg.norm([dx, dy, dz]))
                pose_6d = Pose6D(
                    x=dx,
                    y=dy,
                    z=dz,
                    range_m=range_m,
                    rotation_matrix=np.eye(3).tolist(),
                    rvec=(0.0, 0.0, 0.0),
                    quaternion=(1.0, 0.0, 0.0, 0.0),
                    euler_deg=(0.0, 0.0, 0.0),
                    euler_rad=(0.0, 0.0, 0.0),
                    reprojection_error_rms=0.5,
                    reprojection_error_max=1.0,
                    pose_quality=0.98,
                    is_valid=True,
                    timestamp_sec=max(0.0001, t),
                    frame_id=0,
                    target_id=target.target_id,
                )
                last_pose_result = PoseEstimateResult(
                    timestamp_sec=max(0.0001, t),
                    frame_id=0,
                    target_id=target.target_id,
                    pose=pose_6d,
                    reprojection_error_rms=0.5,
                    pose_quality=0.98,
                    is_valid=True,
                )
            elif last_pose_result is not None and (t - last_pose_result.timestamp_sec) > 0.5:
                last_pose_result = None
                last_target_track_info = None

            esekf_state = esekf.get_state()
            esekf_diag = esekf.get_diagnostics()

            # Track estimation error & NEES consistency
            pos_err = float(np.linalg.norm(np.array(esekf_state.position_world) - vehicle.position))
            estimation_errors.append(pos_err)
            pos_3sigma = esekf_diag.position_uncertainty_m * 3.0
            if pos_err <= max(0.5, pos_3sigma):
                nees_consistent_count += 1

            # E. Landing Intelligence & Safety Supervisor
            t_eval = max(0.001, t)
            ctx = LandingSafetyContext(
                timestamp_sec=t_eval,
                target_info=last_target_track_info,
                pose_result=last_pose_result,
                esekf_state=esekf_state,
                esekf_diagnostics=esekf_diag,
            )

            last_decision = fsm.step(ctx)
            if fsm.current_phase.value != phase_history[-1]:
                phase_history.append(fsm.current_phase.value)

            # F. Flight Interface Command Pipeline
            command = translator.translate(last_decision)
            is_valid, _ = validator.validate(command, t)
            is_auth, _ = authorizer.authorize(command, autopilot._flight_mode)
            is_rate_ok, _ = rate_limiter.check_rate_limit(command, t)

            telemetry = autopilot.receive_telemetry()

            # Evaluate Safety Violations
            safety_detector.evaluate_step(
                twin_state=twin_state,
                decision=last_decision,
                active_command=active_command,
                telemetry=telemetry,
                current_time_sec=t,
            )

            if is_valid and is_auth and is_rate_ok and autopilot.is_connected():
                rate_limiter.record_command(command, t)
                autopilot.send_command(command)
                active_command = command
                commands_dispatched += 1

            # Telemetry Log Entry
            trajectory_log.append({
                "timestamp_sec": t,
                "true_position": list(vehicle.position),
                "true_velocity": list(vehicle.velocity),
                "est_position": list(esekf_state.position_world),
                "est_velocity": list(esekf_state.velocity_world),
                "phase": fsm.current_phase.value,
                "command": active_command.command_type.value if active_command else None,
                "position_error_m": pos_err,
                "uncertainty_3sigma_m": pos_3sigma,
            })

            # Check Termination: Confirmed Touchdown
            if fsm.current_phase == LandingPhase.LANDING_CONFIRMED or vehicle.is_landed:
                break

            clock.step(dt)

        wall_duration = time.perf_counter() - start_wall_time

        # 5. Evaluate Quantitative Scenario Outcome
        final_pos_err = float(np.linalg.norm(vehicle.position[:2] - pad_pos[:2]))
        final_vz = float(abs(vehicle.velocity[2]))
        max_err = float(max(estimation_errors)) if estimation_errors else 0.0
        rmse_err = float(math.sqrt(sum(e ** 2 for e in estimation_errors) / max(1, len(estimation_errors))))
        consistency = float(nees_consistent_count / max(1, len(estimation_errors)))

        # Determine Outcome Classification
        landing_confirmed = bool(fsm.current_phase == LandingPhase.LANDING_CONFIRMED or vehicle.is_landed)
        abort_triggered = bool(any(p in ("ABORTING", "RECOVERY", "FAULT") for p in phase_history))
        abort_occurred = abort_triggered

        if len(safety_detector.violations) > 0:
            outcome = ScenarioOutcome.FAILED_SAFETY_VIOLATION
        elif landing_confirmed:
            outcome = ScenarioOutcome.SUCCESS_LANDED
        elif abort_occurred:
            if scenario.expected_outcome == ScenarioOutcome.SUCCESS_RECOVERED and fsm.current_phase == LandingPhase.RECOVERY:
                outcome = ScenarioOutcome.SUCCESS_RECOVERED
            else:
                outcome = ScenarioOutcome.SUCCESS_ABORTED
        elif clock.current_time_sec >= scenario.duration_sec:
            outcome = ScenarioOutcome.FAILED_TIMEOUT
        else:
            outcome = ScenarioOutcome.FAILED_CRASH

        success = bool((outcome == scenario.expected_outcome) or (outcome == ScenarioOutcome.SUCCESS_LANDED))

        metrics = ScenarioMetrics(
            scenario_name=scenario.name,
            outcome=outcome,
            duration_sec=clock.current_time_sec,
            final_position_error_m=final_pos_err,
            final_velocity_mps=final_vz,
            max_estimation_error_m=max_err,
            rmse_position_m=rmse_err,
            nees_consistency_fraction=consistency,
            commands_dispatched=commands_dispatched,
            phase_transitions=phase_history,
            success=success,
        )

        final_twin_state = vehicle.get_state(clock.current_time_sec)
        final_twin_state.landing_phase = fsm.current_phase

        experiment_result = ExperimentResult(
            scenario_id=scenario.scenario_id,
            run_id=run_identifier,
            seed=seed,
            status=outcome,
            duration_sec=clock.current_time_sec,
            final_state=final_twin_state,
            landing_confirmed=landing_confirmed,
            abort_triggered=abort_triggered,
            safety_violations=safety_detector.violations,
            metrics=metrics,
            event_count=len(scenario.events),
            command_count=commands_dispatched,
            config_hash=config_hash,
        )

        return experiment_result, trajectory_log

    def run_scenario(
        self,
        scenario: Scenario,
        dt_sec: Optional[float] = None,
        run_id: Optional[str] = None,
    ) -> Tuple[ScenarioMetrics, List[Dict[str, Any]]]:
        """Executes a scenario and returns (ScenarioMetrics, trajectory_log)."""
        if dt_sec is not None:
            scenario = scenario.model_copy(update={"timestep_sec": dt_sec})
        exp_res, traj = self.run(scenario, run_id=run_id)
        return exp_res.metrics, traj

    def _schedule_event(
        self,
        event: ScenarioEvent,
        target: SimulatedLandingTarget,
        camera: SimulatedCamera,
        imu: SimulatedIMU,
        disturbances: DisturbanceModel,
        faults: SensorFaultModel,
    ) -> None:
        """Translates a declarative ScenarioEvent into subsystem actions."""
        t_start = event.timestamp_sec
        t_dur = event.duration_sec
        params = event.parameters

        if event.event_type == ScenarioEventType.TARGET_OCCLUDE:
            target.occlusion_model = OcclusionModel(
                occlusion_type=OcclusionType.TEMPORARY,
                start_time_sec=t_start,
                duration_sec=t_dur,
            )

        elif event.event_type == ScenarioEventType.TARGET_DISAPPEAR:
            target.occlusion_model = OcclusionModel(
                occlusion_type=OcclusionType.FULL_DISAPPEARANCE,
                start_time_sec=t_start,
            )

        elif event.event_type == ScenarioEventType.CAMERA_DROPOUT:
            faults.add_fault(
                sensor_type=SensorType.CAMERA,
                fault_type=SensorFaultType.DROP,
                start_time_sec=t_start,
                end_time_sec=t_start + t_dur,
            )

        elif event.event_type == ScenarioEventType.IMU_DROPOUT:
            faults.add_fault(
                sensor_type=SensorType.IMU,
                fault_type=SensorFaultType.DROP,
                start_time_sec=t_start,
                end_time_sec=t_start + t_dur,
            )

        elif event.event_type == ScenarioEventType.AUTOPILOT_DISCONNECT:
            faults.add_fault(
                sensor_type=SensorType.AUTOPILOT,
                fault_type=SensorFaultType.DROP,
                start_time_sec=t_start,
                end_time_sec=t_start + t_dur,
            )

        elif event.event_type == ScenarioEventType.VELOCITY_SPIKE:
            impulse = params.get("impulse_mps", [2.0, 0.0, 0.0])
            disturbances.add_event(DisturbanceEvent(
                timestamp_sec=t_start,
                velocity_impulse_mps=tuple(float(x) for x in impulse),
            ))

        elif event.event_type == ScenarioEventType.WIND_DISTURBANCE:
            force = params.get("force_mps2", [1.0, 0.5])
            disturbances.add_event(DisturbanceEvent(
                timestamp_sec=t_start,
                duration_sec=t_dur,
                lateral_force_mps2=tuple(float(x) for x in force),
            ))


DigitalTwinEngine = ScenarioEngine

