"""Safety violation detector monitoring real-time invariants during simulation."""

from typing import List, Optional
import numpy as np

from skyvanta.core.types import (
    AutopilotTelemetry,
    DigitalTwinState,
    FlightCommand,
    FlightCommandType,
    LandingDecision,
    LandingPhase,
    SafetyViolation,
    SafetyViolationRecord,
)


class SafetyViolationDetector:
    """Evaluates state machine progression and commands against safety invariants."""

    def __init__(
        self,
        max_touchdown_velocity_mps: float = 0.6,
        max_descent_position_uncertainty_m: float = 1.0,
        max_attitude_tilt_deg: float = 35.0,
        stale_target_timeout_sec: float = 1.0,
    ):
        self.max_touchdown_velocity_mps = max_touchdown_velocity_mps
        self.max_descent_position_uncertainty_m = max_descent_position_uncertainty_m
        self.max_attitude_tilt_deg = max_attitude_tilt_deg
        self.stale_target_timeout_sec = stale_target_timeout_sec

        self.violations: List[SafetyViolationRecord] = []
        self._last_target_seen_time: float = -1.0
        self._previous_phase: Optional[LandingPhase] = None

    def record_target_observation(self, timestamp_sec: float) -> None:
        """Records the timestamp of a valid visual target sighting."""
        self._last_target_seen_time = timestamp_sec

    def evaluate_step(
        self,
        twin_state: DigitalTwinState,
        decision: Optional[LandingDecision],
        active_command: Optional[FlightCommand],
        telemetry: Optional[AutopilotTelemetry],
        current_time_sec: float,
    ) -> List[SafetyViolationRecord]:
        """Monitors simulation step for invariant violations."""
        step_violations: List[SafetyViolationRecord] = []

        # 1. Check Landing with High Velocity
        if twin_state.is_landed:
            vz = abs(twin_state.velocity_world[2])
            if vz > self.max_touchdown_velocity_mps:
                rec = SafetyViolationRecord(
                    violation_type=SafetyViolation.LANDING_WITH_HIGH_VELOCITY,
                    timestamp_sec=current_time_sec,
                    message=f"Vehicle touched down with excessive vertical velocity: {vz:.2f} m/s > {self.max_touchdown_velocity_mps} m/s",
                    details={"velocity": list(twin_state.velocity_world)},
                )
                step_violations.append(rec)
                self.violations.append(rec)

        # 2. Check Descent with Stale / Lost Target
        if decision is not None:
            if decision.current_state in (LandingPhase.DESCENDING, LandingPhase.FINAL_APPROACH):
                if self._last_target_seen_time >= 0.0:
                    age = current_time_sec - self._last_target_seen_time
                    if age > self.stale_target_timeout_sec:
                        rec = SafetyViolationRecord(
                            violation_type=SafetyViolation.DESCENT_WITH_STALE_TARGET,
                            timestamp_sec=current_time_sec,
                            message=f"Descent continued with stale visual target (age {age:.2f}s > {self.stale_target_timeout_sec}s)",
                            details={"target_age_sec": age, "phase": decision.current_state.value},
                        )
                        step_violations.append(rec)
                        self.violations.append(rec)

        # 3. Check Descent with High Covariance / Uncertainty
        if decision is not None:
            pos_unc = decision.uncertainty_metrics.get("position_3sigma", 0.0)
            if pos_unc > self.max_descent_position_uncertainty_m:
                if decision.current_state in (LandingPhase.DESCENDING, LandingPhase.FINAL_APPROACH):
                    rec = SafetyViolationRecord(
                        violation_type=SafetyViolation.DESCENT_WITH_HIGH_UNCERTAINTY,
                        timestamp_sec=current_time_sec,
                        message=f"Descent permitted with 3-sigma position uncertainty exceeding limit: {pos_unc:.2f}m > {self.max_descent_position_uncertainty_m}m",
                        details={"uncertainty_m": pos_unc},
                    )
                    step_violations.append(rec)
                    self.violations.append(rec)

        # 4. Check Command After Autopilot Disconnect
        if telemetry is not None and not telemetry.is_connected:
            if active_command is not None and active_command.command_type not in (FlightCommandType.HOLD, FlightCommandType.DISARM):
                rec = SafetyViolationRecord(
                    violation_type=SafetyViolation.COMMAND_AFTER_AUTOPILOT_LOSS,
                    timestamp_sec=current_time_sec,
                    message=f"Command {active_command.command_type.value} issued while autopilot link is disconnected",
                    details={"command_id": active_command.command_id},
                )
                step_violations.append(rec)
                self.violations.append(rec)

        # 5. Check Excessive Attitude Tilt Exceedance
        roll, pitch, _ = twin_state.euler_deg
        if abs(roll) > self.max_attitude_tilt_deg or abs(pitch) > self.max_attitude_tilt_deg:
            rec = SafetyViolationRecord(
                violation_type=SafetyViolation.ATTITUDE_EXCEEDANCE,
                timestamp_sec=current_time_sec,
                message=f"Vehicle attitude exceeded safety tilt envelope: roll={roll:.1f}°, pitch={pitch:.1f}° > {self.max_attitude_tilt_deg}°",
                details={"roll_deg": roll, "pitch_deg": pitch},
            )
            step_violations.append(rec)
            self.violations.append(rec)

        if decision is not None:
            self._previous_phase = decision.current_state

        return step_violations

    def reset(self) -> None:
        """Clears violation history."""
        self.violations.clear()
        self._last_target_seen_time = -1.0
        self._previous_phase = None
