"""Real-time telemetry simulation session, broadcaster, and service management."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket
import numpy as np

from skyvanta.core.config import LandingIntelligenceConfig
from skyvanta.core.types import (
    FlightCommand,
    FrameId,
    LandingDecision,
    LandingPhase,
    LandingSafetyContext,
    Pose6D,
    PoseEstimateResult,
    TrackInfo,
    TrackState,
    VisualPoseMeasurement,
)
from skyvanta.deployment.contracts import TelemetryStreamPacket
from skyvanta.deployment.api.services.simulation_service import ScenarioNotFoundError
from skyvanta.flight.authorization import CommandAuthorizationPolicy
from skyvanta.flight.mock import MockAutopilot
from skyvanta.flight.rate_limiter import CommandRateLimiter
from skyvanta.flight.translation import V7CommandTranslator
from skyvanta.flight.validation import FlightCommandValidator
from skyvanta.fusion.filter import ErrorStateExtendedKalmanFilter
from skyvanta.intelligence.fsm import LandingStateMachine
from skyvanta.simulation.camera import SimulatedCamera
from skyvanta.simulation.clock import SimulationClock
from skyvanta.simulation.disturbances import DisturbanceModel
from skyvanta.simulation.dropout import SensorFaultModel, SensorFaultType, SensorType
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.imu import SimulatedIMU
from skyvanta.simulation.registry import ScenarioRegistry
from skyvanta.simulation.safety import SafetyViolationDetector
from skyvanta.simulation.scenarios import Scenario
from skyvanta.simulation.target import SimulatedLandingTarget
from skyvanta.simulation.vehicle import SimulatedVehicle

logger = logging.getLogger("skyvanta.api.telemetry")


class TelemetrySimulationSession:
    """Manages an active step-by-step 6-DoF digital twin simulation producing telemetry."""

    def __init__(self, scenario: Scenario, rate_hz: float = 20.0):
        self.scenario = scenario
        self.rate_hz = rate_hz
        self.dt = scenario.timestep_sec if scenario.timestep_sec > 0 else (1.0 / rate_hz)

        seed = scenario.seed
        np.random.seed(seed)

        self.clock = SimulationClock(start_time_sec=0.0, default_dt_sec=self.dt)
        self.vehicle = SimulatedVehicle(
            initial_position=scenario.initial_vehicle_pos,
            initial_velocity=scenario.initial_vehicle_vel,
            initial_euler_deg=scenario.initial_vehicle_euler_deg,
        )

        target_cfg = scenario.target_config
        self.target = SimulatedLandingTarget(
            marker_size_m=target_cfg.get("marker_size_m", 0.8),
            initial_position=tuple(target_cfg.get("initial_position", [0.0, 0.0, 0.0])),
            velocity_mps=tuple(target_cfg.get("velocity_mps", [0.0, 0.0, 0.0])),
            target_id=target_cfg.get("target_id", 1),
        )

        noise_cfg = scenario.noise_config
        self.camera = SimulatedCamera(
            pixel_noise_sigma=noise_cfg.camera_pixel_sigma,
            seed=seed,
        )
        self.imu = SimulatedIMU(
            accel_noise_sigma=noise_cfg.imu_accel_sigma,
            gyro_noise_sigma=noise_cfg.imu_gyro_sigma,
            accel_bias=noise_cfg.imu_accel_bias,
            gyro_bias=noise_cfg.imu_gyro_bias,
            accel_drift_rate=noise_cfg.imu_accel_drift_rate,
            gyro_drift_rate=noise_cfg.imu_gyro_drift_rate,
            seed=seed,
        )

        self.disturbances = DisturbanceModel()
        self.faults = SensorFaultModel()
        self.safety_detector = SafetyViolationDetector()

        # Translate declarative events into simulation hooks using existing ScenarioEngine logic
        engine = ScenarioEngine()
        for event in scenario.events:
            engine._schedule_event(
                event, self.target, self.camera, self.imu, self.disturbances, self.faults
            )

        # Initialize V6 ESEKF Filter
        self.esekf = ErrorStateExtendedKalmanFilter()
        p_init = np.diag([0.001] * 3 + [0.001] * 3 + [0.0001] * 3 + [1e-5] * 3 + [1e-4] * 3)
        self.esekf.initialize(
            position=scenario.initial_vehicle_pos,
            velocity=scenario.initial_vehicle_vel,
            rotation_matrix=np.eye(3),
            timestamp_sec=0.0,
            initial_covariance=p_init,
        )

        # Initialize V7 FSM & V8 Command Authorization Pipeline
        self.fsm = LandingStateMachine(LandingIntelligenceConfig())
        self.translator = V7CommandTranslator()
        self.validator = FlightCommandValidator()
        self.authorizer = CommandAuthorizationPolicy()
        self.rate_limiter = CommandRateLimiter(min_interval_sec=0.05)
        self.autopilot = MockAutopilot()
        self.autopilot.connect()

        self.active_command: Optional[FlightCommand] = None
        self.last_target_track_info: Optional[TrackInfo] = None
        self.last_pose_result: Optional[PoseEstimateResult] = None
        self.last_decision: Optional[LandingDecision] = None
        self.is_completed = False

    def step(self) -> Optional[TelemetryStreamPacket]:
        """Executes one simulation timestep and returns a TelemetryStreamPacket."""
        if self.is_completed or self.clock.current_time_sec >= self.scenario.duration_sec:
            self.is_completed = True
            return None

        t = self.clock.current_time_sec
        dt = self.dt
        noise_cfg = self.scenario.noise_config

        # Check Autopilot disconnect fault
        ap_fault = self.faults.get_active_fault(SensorType.AUTOPILOT, t)
        if ap_fault and ap_fault.fault_type == SensorFaultType.DROP:
            self.autopilot.disconnect()

        # A. Step Vehicle Kinematics
        pad_pos = self.target.get_position_at(t)
        twin_state = self.vehicle.step(
            dt_sec=dt,
            current_time_sec=t,
            active_command=self.active_command,
            target_pad_position=tuple(float(x) for x in pad_pos),
            disturbances=self.disturbances,
        )
        accel_true = self.vehicle.acceleration.copy()

        # B. Synthetic Observations
        cam_fault = self.faults.get_active_fault(SensorType.CAMERA, t)
        is_cam_dropped = cam_fault and cam_fault.fault_type == SensorFaultType.DROP

        obs = None
        if not is_cam_dropped:
            obs = self.camera.capture_target_observation(
                drone_pos_world=self.vehicle.position,
                drone_R_world=self.vehicle.rotation_matrix,
                target=self.target,
                current_time_sec=t,
            )

        imu_fault = self.faults.get_active_fault(SensorType.IMU, t)
        is_imu_dropped = imu_fault and imu_fault.fault_type == SensorFaultType.DROP

        imu_meas = None
        if not is_imu_dropped:
            imu_meas = self.imu.generate_measurement(
                drone_accel_world=accel_true,
                drone_R_world=self.vehicle.rotation_matrix,
                drone_omega_body=self.vehicle.angular_velocity,
                current_time_sec=t,
                dt_step_sec=dt,
            )

        # C. ESEKF IMU Propagation
        if imu_meas is not None:
            try:
                self.esekf.propagate(imu_meas)
            except Exception:
                self.esekf.imu_preprocessor.reset()

        # D. Visual Update
        target_visible = False
        if obs is not None:
            noisy_pixels, detection, corners_cam = obs
            self.safety_detector.record_target_observation(t)
            target_visible = True

            p_noise = np.random.normal(0.0, noise_cfg.pose_position_sigma, size=3)
            vis_meas_pos = tuple(float(x) for x in (self.vehicle.position + p_noise))
            var_p = max(0.0025, float(noise_cfg.pose_position_sigma ** 2))
            cov_6x6 = np.diag([var_p] * 3 + [0.001] * 3).tolist()
            vis_meas = VisualPoseMeasurement(
                timestamp_sec=max(0.0001, t),
                position_m=vis_meas_pos,
                rotation_matrix=self.vehicle.rotation_matrix.tolist(),
                quaternion=self.vehicle.quaternion,
                covariance=cov_6x6,
                frame_id=FrameId.WORLD,
                quality=1.0,
                source="simulated_pnp",
                target_id=self.target.target_id,
            )
            self.esekf.update_visual(vis_meas)

            self.last_target_track_info = TrackInfo(
                track_id=self.target.target_id,
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

            dx = float(pad_pos[0] - self.vehicle.position[0])
            dy = float(pad_pos[1] - self.vehicle.position[1])
            dz = float(abs(self.vehicle.position[2] - pad_pos[2]))
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
                target_id=self.target.target_id,
            )
            self.last_pose_result = PoseEstimateResult(
                timestamp_sec=max(0.0001, t),
                frame_id=0,
                target_id=self.target.target_id,
                pose=pose_6d,
                reprojection_error_rms=0.5,
                pose_quality=0.98,
                is_valid=True,
            )
        elif self.last_pose_result is not None and (t - self.last_pose_result.timestamp_sec) > 0.5:
            self.last_pose_result = None
            self.last_target_track_info = None

        esekf_state = self.esekf.get_state()
        esekf_diag = self.esekf.get_diagnostics()
        pos_3sigma = float(esekf_diag.position_uncertainty_m * 3.0)

        # E. FSM & Guidance
        t_eval = max(0.001, t)
        ctx = LandingSafetyContext(
            timestamp_sec=t_eval,
            target_info=self.last_target_track_info,
            pose_result=self.last_pose_result,
            esekf_state=esekf_state,
            esekf_diagnostics=esekf_diag,
        )
        self.last_decision = self.fsm.step(ctx)

        # F. Flight Command & Safety Evaluation
        command = self.translator.translate(self.last_decision)
        is_valid, _ = self.validator.validate(command, t)
        is_auth, _ = self.authorizer.authorize(command, self.autopilot._flight_mode)
        is_rate_ok, _ = self.rate_limiter.check_rate_limit(command, t)

        telemetry = self.autopilot.receive_telemetry()
        self.safety_detector.evaluate_step(
            twin_state=twin_state,
            decision=self.last_decision,
            active_command=self.active_command,
            telemetry=telemetry,
            current_time_sec=t,
        )

        if is_valid and is_auth and is_rate_ok and self.autopilot.is_connected():
            self.rate_limiter.record_command(command, t)
            self.autopilot.send_command(command)
            self.active_command = command

        rec_action = (
            self.last_decision.recommended_action.value
            if self.last_decision and self.last_decision.recommended_action
            else "HOVER"
        )
        is_safe = (len(self.safety_detector.violations) == 0)

        packet = TelemetryStreamPacket(
            packet_type="telemetry",
            scenario_name=self.scenario.name,
            timestamp_sim_sec=round(float(t), 3),
            position_m=[round(float(x), 4) for x in esekf_state.position_world],
            velocity_m_s=[round(float(x), 4) for x in esekf_state.velocity_world],
            attitude_rpy_deg=[round(float(x), 3) for x in self.vehicle.euler_deg],
            landing_phase=self.fsm.current_phase.value,
            recommended_action=rec_action,
            target_visible=target_visible,
            position_uncertainty_3sigma_m=round(float(pos_3sigma), 4),
            is_safe=is_safe,
        )

        if self.fsm.current_phase == LandingPhase.LANDING_CONFIRMED or self.vehicle.is_landed:
            self.is_completed = True

        self.clock.step(dt)
        return packet


class ScenarioBroadcastChannel:
    """Manages telemetry broadcasting from one simulation session to multiple client queues."""

    def __init__(self, scenario: Scenario, rate_hz: float = 20.0):
        self.scenario = scenario
        self.rate_hz = max(1.0, float(rate_hz))
        self.session = TelemetrySimulationSession(scenario, rate_hz=self.rate_hz)
        self.subscribers: Set[asyncio.Queue] = set()
        self.task: Optional[asyncio.Task] = None
        self._is_stopped = False

    def subscribe(self, queue: asyncio.Queue) -> None:
        """Registers a subscriber queue and starts the producer loop if not running."""
        self.subscribers.add(queue)
        if self.task is None or self.task.done():
            self._is_stopped = False
            self.task = asyncio.create_task(self._run_producer())

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unregisters a subscriber queue and stops the task if no subscribers remain."""
        self.subscribers.discard(queue)
        if len(self.subscribers) == 0:
            self.stop()

    def broadcast(self, packet: Optional[TelemetryStreamPacket]) -> None:
        """Broadcasts a telemetry packet to all subscriber queues with bounded backpressure."""
        from skyvanta.deployment.observability.metrics import metrics_collector
        if packet is not None:
            metrics_collector.record_ws_packet_sent(1)

        for queue in list(self.subscribers):
            if queue.full():
                try:
                    _ = queue.get_nowait()
                    metrics_collector.record_ws_packet_dropped(1)
                except Exception:
                    pass
            try:
                queue.put_nowait(packet)
            except Exception:
                pass

    async def _run_producer(self) -> None:
        """Producer loop ticking at the configured rate and streaming telemetry."""
        interval_sec = 1.0 / self.rate_hz
        try:
            while not self._is_stopped and not self.session.is_completed and len(self.subscribers) > 0:
                t0 = time.monotonic()
                packet = self.session.step()
                if packet is None:
                    break
                self.broadcast(packet)
                elapsed = time.monotonic() - t0
                sleep_sec = max(0.0, interval_sec - elapsed)
                await asyncio.sleep(sleep_sec)
        except asyncio.CancelledError:
            pass
        finally:
            self.broadcast(None)
            self._is_stopped = True

    def stop(self) -> None:
        """Stops the producer task and releases resources."""
        self._is_stopped = True
        if self.task and not self.task.done():
            self.task.cancel()
        self.task = None


class TelemetryService:
    """Orchestrates real-time telemetry streaming channels and WebSocket lifecycle."""

    def __init__(self):
        self._channels: Dict[str, ScenarioBroadcastChannel] = {}
        self._active_connections: Set[WebSocket] = set()

    async def get_or_create_channel(
        self,
        scenario_name: str = "nominal_landing",
        rate_hz: float = 20.0,
    ) -> ScenarioBroadcastChannel:
        """Finds or creates a ScenarioBroadcastChannel for the specified benchmark scenario."""
        scenario = ScenarioRegistry.get(scenario_name)
        if scenario is None:
            raise ScenarioNotFoundError(
                f"Benchmark scenario '{scenario_name}' not found in registry."
            )

        channel = self._channels.get(scenario_name)
        if channel is None or channel._is_stopped or channel.session.is_completed:
            channel = ScenarioBroadcastChannel(scenario, rate_hz=rate_hz)
            self._channels[scenario_name] = channel

        return channel

    def register_connection(self, websocket: WebSocket) -> None:
        """Tracks an active WebSocket connection."""
        self._active_connections.add(websocket)

    def unregister_connection(self, websocket: WebSocket) -> None:
        """Removes a WebSocket connection from active tracking."""
        self._active_connections.discard(websocket)

    async def shutdown(self) -> None:
        """Shuts down all telemetry broadcast channels and closes active WebSockets."""
        logger.info("Shutting down TelemetryService: stopping all broadcast channels.")
        for channel in list(self._channels.values()):
            channel.stop()
        self._channels.clear()

        for ws in list(self._active_connections):
            try:
                await ws.close(code=1000, reason="Server shutting down")
            except Exception:
                pass
        self._active_connections.clear()
