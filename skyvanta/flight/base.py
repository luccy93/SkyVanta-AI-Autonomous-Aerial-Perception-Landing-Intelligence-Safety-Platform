"""Abstract base contract for autopilot communication interfaces."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from skyvanta.core.types import (
    AutopilotTelemetry,
    CommandAcknowledgement,
    FlightCommand,
)
from skyvanta.flight.health import AutopilotHealth


class BaseAutopilotInterface(ABC):
    """Abstract protocol for bidirectional communication with an autopilot or vehicle simulator."""

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the autopilot subsystem."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Gracefully terminates connection with the autopilot."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if the interface is connected and active."""
        pass

    @abstractmethod
    def send_command(self, command: FlightCommand) -> CommandAcknowledgement:
        """Dispatches a validated flight command and returns the resulting acknowledgement."""
        pass

    @abstractmethod
    def receive_telemetry(self) -> Optional[AutopilotTelemetry]:
        """Polls for the latest available vehicle telemetry packet."""
        pass

    @abstractmethod
    def get_health(self) -> AutopilotHealth:
        """Evaluates communication health, heartbeat status, and error states."""
        pass

    @abstractmethod
    def send_heartbeat(self, timestamp_sec: float) -> bool:
        """Sends a periodic heartbeat signal to keep the interface link active."""
        pass
