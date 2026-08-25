"""Deterministic mock autopilot and software-in-the-loop vehicle simulator."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from skyvanta.core.config import CommandConfig, HeartbeatConfig
from skyvanta.core.types import (
    AutopilotHealthStatus,
    AutopilotTelemetry,
    CommandAcknowledgement,
    CommandStatus,
    FlightCommand,
    FlightCommandType,
    FlightMode,
    FrameId,
)
from skyvanta.flight.base import BaseAutopilotInterface
from skyvanta.flight.health import AutopilotHealth, HeartbeatMonitor


class MockAutopilot(BaseAutopilotInterface):
    """Deterministic simulation of an external autopilot vehicle interface.

    Simulates:
    - Autopilot state transitions and flight modes
    - Vehicle kinematic propagation
    - Command acknowledgement, execution, and timeouts
    - Heartbeat tracking and simulated link loss
    """

    def __init__(
        self,
        command_config: Optional[CommandConfig] = None,
        heartbeat_config: Optional[HeartbeatConfig] = None,
        initial_position: Tuple[float, float, float] = (0.0, 0.0, 10.0),
    ):
        self.command_config = command_config or CommandConfig()
        self.heartbeat_config = heartbeat_config or HeartbeatConfig()
        self.heartbeat_monitor = HeartbeatMonitor(self.heartbeat_config)

        self._is_connected: bool = False
        self._is_armed: bool = False
        self._flight_mode: FlightMode = FlightMode.DISCONNECTED

        # Simulated vehicle state
        self._position: List[float] = list(initial_position)
        self._velocity: List[float] = [0.0, 0.0, 0.0]
        self._orientation_rpy: List[float] = [0.0, 0.0, 0.0]
        self._current_time: float = 0.0

        # Command tracking & execution
        self._active_command: Optional[FlightCommand] = None
        self._command_history: List[FlightCommand] = []
        self._acknowledgements: List[CommandAcknowledgement] = []

        # Fault injection flags for automated testing
        self._force_ack_timeout: bool = False
        self._force_rejection: bool = False
        self._rejection_reason: str = "Simulated rejection"

    def connect(self) -> bool:
        """Connects mock autopilot and transitions to STANDBY."""
        self._is_connected = True
        self._flight_mode = FlightMode.STANDBY
        self._is_armed = True
        return True

    def disconnect(self) -> None:
        """Disconnects mock autopilot and transitions to DISCONNECTED."""
        self._is_connected = False
        self._flight_mode = FlightMode.DISCONNECTED
        self._is_armed = False
        self.heartbeat_monitor.reset()

    def is_connected(self) -> bool:
        """Returns connection state."""
        return self._is_connected

    def send_command(self, command: FlightCommand) -> CommandAcknowledgement:
        """Processes a flight command and returns an acknowledgement."""
        t_now = command.timestamp_sec
        self._current_time = t_now
        self._command_history.append(command)

        if not self._is_connected:
            ack = CommandAcknowledgement(
                command_id=command.command_id,
                sequence_number=command.sequence_number,
                status=CommandStatus.REJECTED,
                timestamp_sec=t_now,
                reason="Autopilot is disconnected",
            )
            self._acknowledgements.append(ack)
            return ack

        if self._force_ack_timeout:
            ack = CommandAcknowledgement(
                command_id=command.command_id,
                sequence_number=command.sequence_number,
                status=CommandStatus.TIMEOUT,
                timestamp_sec=t_now,
                reason="Simulated command acknowledgement timeout",
            )
            self._acknowledgements.append(ack)
            return ack

        if self._force_rejection:
            ack = CommandAcknowledgement(
                command_id=command.command_id,
                sequence_number=command.sequence_number,
                status=CommandStatus.REJECTED,
                timestamp_sec=t_now,
                reason=self._rejection_reason,
            )
            self._acknowledgements.append(ack)
            return ack

        if t_now > command.expiration_sec:
            ack = CommandAcknowledgement(
                command_id=command.command_id,
                sequence_number=command.sequence_number,
                status=CommandStatus.EXPIRED,
                timestamp_sec=t_now,
                reason=f"Command expired: {t_now:.3f} > {command.expiration_sec:.3f}",
            )
            self._acknowledgements.append(ack)
            return ack

        # Execute command state update
        self._active_command = command
        self._update_flight_mode_from_command(command.command_type)

        ack = CommandAcknowledgement(
            command_id=command.command_id,
            sequence_number=command.sequence_number,
            status=CommandStatus.ACCEPTED,
            timestamp_sec=t_now,
            reason=f"Command {command.command_type.value} accepted",
            autopilot_state={"flight_mode": self._flight_mode.value, "altitude": self._position[2]},
        )
        self._acknowledgements.append(ack)
        return ack

    def step(self, dt: float = 0.05) -> None:
        """Simulates vehicle kinematics over duration dt."""
        self._current_time += dt

        if not self._is_connected:
            return

        if self._active_command is None:
            return

        cmd = self._active_command.command_type
        if cmd == FlightCommandType.DESCEND:
            # Descend at 0.5 m/s
            self._velocity = [0.0, 0.0, -0.5]
            self._position[2] = max(0.0, self._position[2] - 0.5 * dt)
        elif cmd == FlightCommandType.FINAL_APPROACH:
            # Slower final descent at 0.2 m/s
            self._velocity = [0.0, 0.0, -0.2]
            self._position[2] = max(0.0, self._position[2] - 0.2 * dt)
        elif cmd == FlightCommandType.ABORT:
            # Climb out at 1.0 m/s to safe altitude (15m)
            self._velocity = [0.0, 0.0, 1.0]
            self._position[2] = min(15.0, self._position[2] + 1.0 * dt)
        elif cmd == FlightCommandType.HOLD:
            self._velocity = [0.0, 0.0, 0.0]
        elif cmd == FlightCommandType.CONFIRM_LANDING:
            self._velocity = [0.0, 0.0, 0.0]
            self._position[2] = 0.0

    def receive_telemetry(self) -> Optional[AutopilotTelemetry]:
        """Returns the current simulated vehicle telemetry."""
        if not self._is_connected:
            return None

        return AutopilotTelemetry(
            timestamp_sec=self._current_time,
            is_connected=self._is_connected,
            is_armed=self._is_armed,
            flight_mode=self._flight_mode,
            position_m=tuple(self._position),
            velocity_mps=tuple(self._velocity),
            orientation_rpy_deg=tuple(self._orientation_rpy),
            altitude_m=float(self._position[2]),
            frame_id=FrameId.WORLD,
            is_simulation=True,
        )

    def get_health(self) -> AutopilotHealth:
        """Returns communication and connection health."""
        if not self._is_connected:
            return AutopilotHealth(
                connected=False,
                heartbeat_ok=False,
                telemetry_ok=False,
                command_channel_ok=False,
                health_status=AutopilotHealthStatus.DISCONNECTED,
                last_message_time=self._current_time,
                failure_reason="Autopilot interface is disconnected",
            )
        return self.heartbeat_monitor.check_health(self._current_time)

    def send_heartbeat(self, timestamp_sec: float) -> bool:
        """Records a heartbeat tick."""
        if not self._is_connected:
            return False
        self._current_time = timestamp_sec
        self.heartbeat_monitor.record_heartbeat(timestamp_sec)
        return True

    def _update_flight_mode_from_command(self, cmd_type: FlightCommandType) -> None:
        """Maps incoming flight commands to autopilot flight modes."""
        if cmd_type == FlightCommandType.ABORT:
            self._flight_mode = FlightMode.ABORT
        elif cmd_type in (FlightCommandType.DESCEND, FlightCommandType.FINAL_APPROACH, FlightCommandType.CONFIRM_LANDING):
            self._flight_mode = FlightMode.LANDING
        elif cmd_type in (FlightCommandType.SEARCH, FlightCommandType.ALIGN, FlightCommandType.APPROACH):
            self._flight_mode = FlightMode.GUIDED
        elif cmd_type == FlightCommandType.HOLD:
            self._flight_mode = FlightMode.GUIDED

    # Fault injection controls
    def set_fault_injection(
        self,
        force_timeout: bool = False,
        force_rejection: bool = False,
        rejection_reason: str = "Simulated fault",
    ) -> None:
        """Configures simulated faults for test validation."""
        self._force_ack_timeout = force_timeout
        self._force_rejection = force_rejection
        self._rejection_reason = rejection_reason
