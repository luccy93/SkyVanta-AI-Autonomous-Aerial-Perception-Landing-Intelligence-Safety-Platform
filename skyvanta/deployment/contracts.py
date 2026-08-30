"""Deployment data contracts, health schemas, and API request/response models."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    """Service health state classification."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class SimulationStatus(str, Enum):
    """Simulation engine runtime state."""
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ERROR = "error"


class DeploymentHealthContract(BaseModel):
    """Formal schema for the /health deployment health contract."""

    status: HealthStatus = Field(
        description="Overall service health state (healthy, degraded, unhealthy).",
    )
    service: str = Field(
        default="skyvanta-api",
        description="Deployment service identifier.",
    )
    version: str = Field(
        description="Software release version string.",
    )
    environment: str = Field(
        description="Deployment environment (development, testing, production).",
    )
    uptime_sec: float = Field(
        description="Elapsed wall-clock uptime in seconds since process start.",
    )
    simulation_engine: SimulationStatus = Field(
        description="State of the digital twin simulation subsystem.",
    )
    available_scenarios_count: int = Field(
        description="Number of verified benchmark scenarios registered in the catalog.",
    )
    hardware_access: bool = Field(
        default=False,
        description="Whether physical drone hardware/serial ports are accessible (always False).",
    )
    network_model_download: bool = Field(
        default=False,
        description="Whether runtime network weight downloading is allowed (always False).",
    )
    safety_boundary_enforced: bool = Field(
        default=True,
        description="Whether software safety invariants and rate limiters are active.",
    )
    timestamp_sec: float = Field(
        description="Unix timestamp when health check was evaluated.",
    )


class ScenarioRunRequest(BaseModel):
    """Request payload to initiate a digital twin simulation scenario."""

    scenario_name: str = Field(
        default="nominal_landing",
        description="Name of registered benchmark scenario to execute.",
    )
    seed: int = Field(
        default=42,
        description="Deterministic random seed for simulation reproducibility.",
    )
    max_duration_sec: Optional[float] = Field(
        default=None,
        description="Optional execution timeout override in seconds.",
    )
    enable_noise: bool = Field(
        default=True,
        description="Whether synthetic sensor noise (Gaussian, drift, jitter) is active.",
    )


class ScenarioRunResponse(BaseModel):
    """Response payload returned upon digital twin simulation completion."""

    run_id: str = Field(
        description="Unique execution identifier for the simulation run.",
    )
    scenario_name: str = Field(
        description="Name of the executed benchmark scenario.",
    )
    status: str = Field(
        description="Final landing outcome (SUCCESS_LANDED, ABORTED, TIMED_OUT, etc.).",
    )
    seed: int = Field(
        description="Random seed utilized during execution.",
    )
    duration_sim_sec: float = Field(
        description="Simulated mission elapsed time in seconds.",
    )
    duration_wall_sec: float = Field(
        description="Real-world wall-clock computation time in seconds.",
    )
    realtime_factor: float = Field(
        description="Execution speed multiplier relative to real-time wall clock.",
    )
    final_position_error_m: float = Field(
        description="Distance from vehicle touchdown position to landing pad center.",
    )
    rmse_position_m: float = Field(
        description="Root-mean-squared 3D position error over the flight trajectory.",
    )
    safety_violations_count: int = Field(
        description="Total number of hard safety invariant breaches detected (0 for PASS).",
    )
    is_success: bool = Field(
        description="Whether all scenario pass criteria were satisfied.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Optional failure or exception diagnostic details.",
    )


class TelemetryStreamPacket(BaseModel):
    """Real-time telemetry packet streamed across the WebSocket boundary."""

    packet_type: str = Field(
        default="telemetry",
        description="Packet type classification identifier.",
    )
    scenario_name: Optional[str] = Field(
        default=None,
        description="Active benchmark scenario identifier.",
    )
    timestamp_sim_sec: float = Field(
        description="Simulated mission timestamp in seconds.",
    )
    position_m: List[float] = Field(
        description="Estimated 3D position [x, y, z] in meters (ENU).",
    )
    velocity_m_s: List[float] = Field(
        description="Estimated 3D velocity [vx, vy, vz] in m/s.",
    )
    attitude_rpy_deg: List[float] = Field(
        description="Vehicle orientation [roll, pitch, yaw] in degrees.",
    )
    landing_phase: str = Field(
        description="Current operational FSM landing phase.",
    )
    recommended_action: str = Field(
        description="Active guidance command recommended by the Safety Supervisor.",
    )
    target_visible: bool = Field(
        description="Whether the landing target pad is currently tracked by perception.",
    )
    position_uncertainty_3sigma_m: float = Field(
        description="3-sigma position estimation covariance envelope in meters.",
    )
    is_safe: bool = Field(
        description="Real-time multi-invariant safety evaluation boolean.",
    )


class DeploymentReadinessContract(BaseModel):
    """Formal schema for the /ready operational readiness contract."""

    ready: bool = Field(
        description="Whether the service is prepared to accept traffic.",
    )
    status: str = Field(
        description="Readiness status ('ready' or 'not_ready').",
    )
    service: str = Field(
        default="skyvanta-api",
        description="Deployment service identifier.",
    )
    version: str = Field(
        description="Software release version string.",
    )
    environment: str = Field(
        description="Deployment environment (development, testing, production).",
    )
    checks: Dict[str, bool] = Field(
        description="Detailed verification results for genuine operational dependencies.",
    )
    uptime_sec: float = Field(
        description="Elapsed wall-clock uptime in seconds.",
    )
    timestamp_sec: float = Field(
        description="Unix timestamp when readiness was evaluated.",
    )


class MetricsResponseContract(BaseModel):
    """Formal schema for the /api/v1/metrics operational monitoring endpoint."""

    service: str = Field(
        default="skyvanta-api",
        description="Deployment service identifier.",
    )
    version: str = Field(
        description="Software release version.",
    )
    environment: str = Field(
        description="Active deployment tier.",
    )
    timestamp_sec: float = Field(
        description="Evaluation timestamp in seconds.",
    )
    http: Dict[str, Any] = Field(
        description="HTTP request volume, status breakdown, and latency percentiles.",
    )
    errors: Dict[str, int] = Field(
        description="Categorized error counters.",
    )
    websockets: Dict[str, Any] = Field(
        description="WebSocket connection counts, stream rates, and packet metrics.",
    )
    scenarios: Dict[str, Any] = Field(
        description="Scenario execution metrics and compliance summaries.",
    )
    system: Dict[str, Any] = Field(
        description="Runtime system resources (CPU, memory, uptime, version).",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Active operational resource and performance threshold warnings.",
    )
    recent_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent structured operational audit events (sanitized, bounded).",
    )
