"""Autopilot connection health tracking, heartbeat monitoring, and failsafe supervision."""

from typing import Optional
from pydantic import BaseModel, Field

from skyvanta.core.config import HeartbeatConfig
from skyvanta.core.types import AutopilotHealthStatus, FlightMode


class AutopilotHealth(BaseModel):
    """Real-time health status of the autopilot communication interface."""
    connected: bool = Field(default=True, description="Physical/logical connection state")
    heartbeat_ok: bool = Field(default=True, description="Heartbeat within timeout threshold")
    telemetry_ok: bool = Field(default=True, description="Telemetry stream active and valid")
    command_channel_ok: bool = Field(default=True, description="Command dispatch channel responsive")
    health_status: AutopilotHealthStatus = Field(default=AutopilotHealthStatus.HEALTHY)
    last_message_time: float = Field(default=0.0, description="Timestamp of last received packet")
    last_command_time: float = Field(default=0.0, description="Timestamp of last dispatched command")
    failure_reason: Optional[str] = Field(default=None, description="Diagnostic error or failure description")


class HeartbeatMonitor:
    """Monitors periodic heartbeat signals and declares connection loss upon timeout."""

    def __init__(self, config: Optional[HeartbeatConfig] = None):
        self.config = config or HeartbeatConfig()
        self._last_heartbeat_sec: float = 0.0
        self._is_active: bool = False

    def record_heartbeat(self, timestamp_sec: float) -> None:
        """Records reception of a valid heartbeat packet."""
        self._last_heartbeat_sec = timestamp_sec
        self._is_active = True

    def check_health(self, current_time_sec: float) -> AutopilotHealth:
        """Evaluates heartbeat freshness and connection status."""
        if not self._is_active or self._last_heartbeat_sec <= 0.0:
            return AutopilotHealth(
                connected=False,
                heartbeat_ok=False,
                telemetry_ok=False,
                command_channel_ok=False,
                health_status=AutopilotHealthStatus.DISCONNECTED,
                last_message_time=self._last_heartbeat_sec,
                failure_reason="No heartbeat received yet",
            )

        age = current_time_sec - self._last_heartbeat_sec
        if age > self.config.timeout_sec:
            return AutopilotHealth(
                connected=False,
                heartbeat_ok=False,
                telemetry_ok=False,
                command_channel_ok=False,
                health_status=AutopilotHealthStatus.DISCONNECTED,
                last_message_time=self._last_heartbeat_sec,
                failure_reason=f"Heartbeat timeout: age {age:.2f}s exceeds threshold {self.config.timeout_sec:.2f}s",
            )

        if age > self.config.expected_interval_sec * 1.5:
            return AutopilotHealth(
                connected=True,
                heartbeat_ok=True,
                telemetry_ok=True,
                command_channel_ok=True,
                health_status=AutopilotHealthStatus.DEGRADED,
                last_message_time=self._last_heartbeat_sec,
                failure_reason=f"Heartbeat delayed: age {age:.2f}s > {self.config.expected_interval_sec * 1.5:.2f}s",
            )

        return AutopilotHealth(
            connected=True,
            heartbeat_ok=True,
            telemetry_ok=True,
            command_channel_ok=True,
            health_status=AutopilotHealthStatus.HEALTHY,
            last_message_time=self._last_heartbeat_sec,
            failure_reason=None,
        )

    def reset(self) -> None:
        """Resets the monitor state."""
        self._last_heartbeat_sec = 0.0
        self._is_active = False
