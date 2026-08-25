"""End-to-end flight interface and landing simulation harness (Volume 7 -> Volume 8)."""

from typing import Any, Dict, List, Optional, Tuple

from skyvanta.core.config import FlightInterfaceConfig, LandingIntelligenceConfig
from skyvanta.core.exceptions import FlightInterfaceError
from skyvanta.core.types import (
    AutopilotTelemetry,
    CommandAcknowledgement,
    CommandStatus,
    FlightCommand,
    FlightCommandType,
    FlightMode,
    LandingDecision,
    LandingSafetyContext,
    RecommendedAction,
)
from skyvanta.flight.authorization import CommandAuthorizationPolicy
from skyvanta.flight.logger import FlightEventLogger
from skyvanta.flight.mock import MockAutopilot
from skyvanta.flight.rate_limiter import CommandRateLimiter
from skyvanta.flight.telemetry import TelemetryValidator
from skyvanta.flight.translation import V7CommandTranslator
from skyvanta.flight.validation import FlightCommandValidator
from skyvanta.intelligence.fsm import LandingStateMachine


class FlightSimulationHarness:
    """Integrated simulation pipeline coordinating V7 Intelligence with V8 Flight Interface and Mock Autopilot."""

    def __init__(
        self,
        flight_config: Optional[FlightInterfaceConfig] = None,
        intelligence_config: Optional[LandingIntelligenceConfig] = None,
    ):
        self.flight_config = flight_config or FlightInterfaceConfig()
        self.intelligence_config = intelligence_config or LandingIntelligenceConfig()

        # Strict safety check: external mode must not be enabled by default
        if self.flight_config.mode == "external" and not self.flight_config.safety.allow_external:
            raise FlightInterfaceError(
                "External autopilot connection rejected: safety.allow_external is False. "
                "SkyVanta AI operates strictly in SIMULATION mode by default."
            )

        # Core subsystems
        self.fsm = LandingStateMachine(self.intelligence_config)
        self.translator = V7CommandTranslator(self.flight_config.command)
        self.validator = FlightCommandValidator()
        self.authorizer = CommandAuthorizationPolicy(
            require_v7_authorization=self.flight_config.safety.require_v7_authorization
        )
        self.rate_limiter = CommandRateLimiter(self.flight_config.command.min_interval_sec)
        self.telemetry_validator = TelemetryValidator()
        self.autopilot = MockAutopilot(
            command_config=self.flight_config.command,
            heartbeat_config=self.flight_config.heartbeat,
        )

        # Connect simulation autopilot by default
        self.autopilot.connect()
        self.autopilot.send_heartbeat(0.0)

        self.execution_log: List[Dict[str, Any]] = []

    def step(
        self,
        context: LandingSafetyContext,
        dt_sec: float = 0.05,
    ) -> Tuple[
        LandingDecision,
        Optional[FlightCommand],
        Optional[CommandAcknowledgement],
        Optional[AutopilotTelemetry],
    ]:
        """Executes a single end-to-end perception -> intelligence -> command -> simulation cycle.

        Args:
            context: LandingSafetyContext from perception and ESEKF.
            dt_sec: Time step in seconds.

        Returns:
            (landing_decision, flight_command, acknowledgement, telemetry)
        """
        t_now = context.timestamp_sec

        # 1. Update autopilot heartbeat
        self.autopilot.send_heartbeat(t_now)

        # 2. V7 Intelligence Decision
        decision = self.fsm.step(context)

        # 3. Translate V7 Decision to V8 FlightCommand
        command = self.translator.translate(decision)
        FlightEventLogger.log_event(
            event_type="COMMAND_CREATED",
            timestamp_sec=t_now,
            command=command,
        )

        # 4. Command Validation
        is_valid, val_reason = self.validator.validate(command, t_now)
        if not is_valid:
            command.is_valid = False
            command.rejection_reason = val_reason
            FlightEventLogger.log_event(
                event_type="COMMAND_REJECTED",
                timestamp_sec=t_now,
                command=command,
                reason=val_reason,
            )
            ack = CommandAcknowledgement(
                command_id=command.command_id,
                sequence_number=command.sequence_number,
                status=CommandStatus.REJECTED,
                timestamp_sec=t_now,
                reason=val_reason,
            )
            return decision, command, ack, self.autopilot.receive_telemetry()

        FlightEventLogger.log_event(
            event_type="COMMAND_VALIDATED",
            timestamp_sec=t_now,
            command=command,
        )

        # 5. Command Authorization
        current_flight_mode = (
            self.autopilot._flight_mode if self.autopilot.is_connected() else FlightMode.DISCONNECTED
        )
        is_auth, auth_reason = self.authorizer.authorize(command, current_flight_mode)
        if not is_auth:
            command.is_valid = False
            command.rejection_reason = auth_reason
            FlightEventLogger.log_event(
                event_type="COMMAND_REJECTED",
                timestamp_sec=t_now,
                command=command,
                reason=auth_reason,
            )
            ack = CommandAcknowledgement(
                command_id=command.command_id,
                sequence_number=command.sequence_number,
                status=CommandStatus.UNSAFE if "progression" in (auth_reason or "") else CommandStatus.REJECTED,
                timestamp_sec=t_now,
                reason=auth_reason,
            )
            return decision, command, ack, self.autopilot.receive_telemetry()

        FlightEventLogger.log_event(
            event_type="COMMAND_AUTHORIZED",
            timestamp_sec=t_now,
            command=command,
        )

        # 6. Rate Limiting and Duplicate Check
        is_rate_ok, rate_reason = self.rate_limiter.check_rate_limit(command, t_now)
        if not is_rate_ok:
            FlightEventLogger.log_event(
                event_type="COMMAND_RATE_LIMITED",
                timestamp_sec=t_now,
                command=command,
                reason=rate_reason,
            )
            ack = CommandAcknowledgement(
                command_id=command.command_id,
                sequence_number=command.sequence_number,
                status=CommandStatus.BUSY,
                timestamp_sec=t_now,
                reason=rate_reason,
            )
            return decision, command, ack, self.autopilot.receive_telemetry()

        self.rate_limiter.record_command(command, t_now)

        # 7. Dispatch to Mock Autopilot
        FlightEventLogger.log_event(
            event_type="COMMAND_SENT",
            timestamp_sec=t_now,
            command=command,
        )
        ack = self.autopilot.send_command(command)
        FlightEventLogger.log_event(
            event_type="COMMAND_ACKNOWLEDGED",
            timestamp_sec=t_now,
            command=command,
            ack=ack,
        )

        # 8. Step Mock Autopilot Kinematics
        self.autopilot.step(dt_sec)

        # 9. Receive and Validate Telemetry
        telemetry = self.autopilot.receive_telemetry()
        if telemetry is not None:
            self.telemetry_validator.validate_or_raise(telemetry)

        # Record step in log
        self.execution_log.append({
            "timestamp": t_now,
            "decision": decision.model_dump(),
            "command": command.model_dump(),
            "acknowledgement": ack.model_dump(),
            "telemetry": telemetry.model_dump() if telemetry else None,
        })

        return decision, command, ack, telemetry

    def reset(self) -> None:
        """Resets the simulation harness state."""
        self.fsm.reset()
        self.translator.reset_sequence()
        self.rate_limiter.reset()
        self.autopilot.connect()
        self.execution_log.clear()
