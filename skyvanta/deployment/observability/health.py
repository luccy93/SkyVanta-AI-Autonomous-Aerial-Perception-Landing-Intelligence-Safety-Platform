"""Readiness inspection service and operational dependency verification."""

import time
from typing import Dict, Optional
from pydantic import BaseModel, Field

from skyvanta.core.config import SkyVantaConfig
from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.observability.events import EventType, event_logger
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.registry import ScenarioRegistry

try:
    import importlib.metadata as importlib_metadata
    __version__ = importlib_metadata.version("skyvanta")
except Exception:
    __version__ = "0.1.0"


class DeploymentReadinessContract(BaseModel):
    """Schema for the /ready operational readiness contract."""

    ready: bool = Field(description="Whether the service is fully prepared to accept traffic.")
    status: str = Field(description="Readiness status ('ready' or 'not_ready').")
    service: str = Field(default="skyvanta-api", description="Service identifier.")
    version: str = Field(description="Software release version string.")
    environment: str = Field(description="Deployment environment (development, testing, production).")
    checks: Dict[str, bool] = Field(description="Detailed verification results for genuine dependencies.")
    uptime_sec: float = Field(description="Elapsed wall-clock uptime in seconds.")
    timestamp_sec: float = Field(description="Unix timestamp when readiness was evaluated.")


class ReadinessService:
    """Evaluates genuine operational dependencies to determine service traffic readiness."""

    def __init__(self):
        self._start_time = time.time()
        self._has_emitted_ready_event = False

    @property
    def uptime_sec(self) -> float:
        """Returns elapsed wall-clock uptime in seconds."""
        return float(time.time() - self._start_time)

    def check_readiness(
        self,
        deployment_config: Optional[DeploymentConfig] = None,
        platform_config: Optional[SkyVantaConfig] = None,
    ) -> DeploymentReadinessContract:
        """Evaluates readiness of all verified operational subsystems.

        Checks:
        1. Scenario registry catalog loaded (>= 10 benchmark scenarios)
        2. Simulation engine instantiable
        3. Hardware isolation compliance (allow_external == False)
        4. Network model download compliance (allow_network_download == False)

        Returns:
            DeploymentReadinessContract instance.
        """
        dep_cfg = deployment_config or DeploymentConfig.from_env()
        plat_cfg = platform_config or SkyVantaConfig()

        checks: Dict[str, bool] = {}

        # 1. Check Scenario Registry
        scenarios = ScenarioRegistry.list_all()
        checks["scenario_catalog_loaded"] = len(scenarios) >= 10

        # 2. Check Simulation Engine
        try:
            _ = ScenarioEngine()
            checks["simulation_engine_ready"] = True
        except Exception:
            checks["simulation_engine_ready"] = False

        # 3. Check Safety & Isolation Invariants
        hardware_isolated = (
            not dep_cfg.allow_external
            and not plat_cfg.flight_interface.safety.allow_external
            and dep_cfg.hardware_disconnected
        )
        network_isolated = (
            not dep_cfg.allow_network_download
            and not plat_cfg.detector.allow_network_download
        )
        checks["safety_invariants_enforced"] = bool(hardware_isolated and network_isolated)

        is_ready = all(checks.values())
        status_str = "ready" if is_ready else "not_ready"

        if is_ready and not self._has_emitted_ready_event:
            self._has_emitted_ready_event = True
            event_logger.emit(
                event_type=EventType.SERVICE_READY,
                message="SkyVanta AI service is verified ready to serve traffic",
                severity="INFO",
                details={
                    "version": __version__,
                    "environment": dep_cfg.environment.value,
                    "available_scenarios": len(scenarios),
                },
                environment=dep_cfg.environment.value,
            )

        return DeploymentReadinessContract(
            ready=is_ready,
            status=status_str,
            service="skyvanta-api",
            version=__version__,
            environment=dep_cfg.environment.value,
            checks=checks,
            uptime_sec=round(self.uptime_sec, 3),
            timestamp_sec=round(time.time(), 3),
        )


# Global singleton instance
readiness_service = ReadinessService()
