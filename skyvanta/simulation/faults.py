"""Deterministic fault injection schedules and perturbation managers."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class FaultType(str, Enum):
    """Catalog of deterministic fault types injected into the Digital Twin."""
    OPTICAL_DROPOUT = "OPTICAL_DROPOUT"
    HIGH_WIND_GUST = "HIGH_WIND_GUST"
    IMU_BIAS_SHIFT = "IMU_BIAS_SHIFT"
    AUTOPILOT_DISCONNECT = "AUTOPILOT_DISCONNECT"
    PAD_MOTION = "PAD_MOTION"
    REPROJECTION_ERROR_INJECTION = "REPROJECTION_ERROR_INJECTION"


class FaultEvent(BaseModel):
    """Scheduled fault injection window."""
    fault_type: FaultType
    start_time_sec: float
    end_time_sec: float
    parameters: Dict[str, Any] = Field(default_factory=dict)


class FaultSchedule:
    """Manages scheduled fault occurrences during scenario simulation."""

    def __init__(self, faults: Optional[List[FaultEvent]] = None):
        self.faults: List[FaultEvent] = faults or []

    def add_fault(
        self,
        fault_type: FaultType,
        start_time_sec: float,
        end_time_sec: float,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Schedules a new fault injection."""
        self.faults.append(
            FaultEvent(
                fault_type=fault_type,
                start_time_sec=start_time_sec,
                end_time_sec=end_time_sec,
                parameters=parameters or {},
            )
        )

    def is_fault_active(self, fault_type: FaultType, t_sec: float) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Returns True and parameter payload if a specific fault is active at time t."""
        for fault in self.faults:
            if fault.fault_type == fault_type and fault.start_time_sec <= t_sec <= fault.end_time_sec:
                return True, fault.parameters
        return False, None
