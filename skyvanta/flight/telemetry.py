"""Autopilot telemetry validation and spatial sanity checks."""

import math
from typing import Optional, Tuple
import numpy as np

from skyvanta.core.exceptions import FlightInterfaceError
from skyvanta.core.types import AutopilotTelemetry, FrameId


class TelemetryValidator:
    """Validates structural correctness, finite numerical bounds, and physical sanity of telemetry packets."""

    def __init__(self, max_speed_mps: float = 30.0, max_altitude_m: float = 1000.0):
        self.max_speed_mps = max_speed_mps
        self.max_altitude_m = max_altitude_m

    def validate(self, telemetry: AutopilotTelemetry) -> Tuple[bool, Optional[str]]:
        """Evaluates telemetry validity.

        Args:
            telemetry: AutopilotTelemetry instance to inspect.

        Returns:
            (is_valid, failure_reason)
        """
        # 1. Timestamp checks
        if telemetry.timestamp_sec <= 0.0 or not np.isfinite(telemetry.timestamp_sec):
            return False, f"Invalid telemetry timestamp: {telemetry.timestamp_sec}"

        # 2. Numerical finiteness
        for name, val in [
            ("position", telemetry.position_m),
            ("velocity", telemetry.velocity_mps),
            ("orientation", telemetry.orientation_rpy_deg),
        ]:
            if not all(np.isfinite(x) for x in val):
                return False, f"Telemetry contains non-finite values in {name}: {val}"

        if not np.isfinite(telemetry.altitude_m):
            return False, f"Non-finite altitude: {telemetry.altitude_m}"

        # 3. Physical bounds
        speed = math.sqrt(sum(v ** 2 for v in telemetry.velocity_mps))
        if speed > self.max_speed_mps:
            return False, f"Telemetry speed {speed:.2f} m/s exceeds max allowable limit {self.max_speed_mps} m/s"

        if telemetry.altitude_m < -5.0 or telemetry.altitude_m > self.max_altitude_m:
            return False, f"Altitude {telemetry.altitude_m:.2f} m is outside safe operational bounds [-5.0, {self.max_altitude_m}]"

        # 4. Frame validity
        if telemetry.frame_id not in (FrameId.WORLD, FrameId.BODY):
            return False, f"Telemetry frame {telemetry.frame_id} must be WORLD or BODY"

        return True, None

    def validate_or_raise(self, telemetry: AutopilotTelemetry) -> None:
        """Validates telemetry and raises FlightInterfaceError if invalid."""
        is_valid, reason = self.validate(telemetry)
        if not is_valid:
            raise FlightInterfaceError(f"Telemetry validation failed: {reason}")
