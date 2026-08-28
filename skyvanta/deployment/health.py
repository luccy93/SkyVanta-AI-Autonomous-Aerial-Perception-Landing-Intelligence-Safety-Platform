"""Health check inspection service for container and API deployment."""

import time
from typing import Optional

from skyvanta.core.config import SkyVantaConfig
from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.contracts import (
    DeploymentHealthContract,
    HealthStatus,
    SimulationStatus,
)
from skyvanta.simulation.registry import ScenarioRegistry

try:
    import importlib.metadata as importlib_metadata
    __version__ = importlib_metadata.version("skyvanta")
except Exception:
    __version__ = "0.1.0"


class HealthCheckService:
    """Evaluates deployment subsystem health, configuration status, and safety invariants."""

    def __init__(self):
        self._start_time = time.time()

    @property
    def uptime_sec(self) -> float:
        """Returns elapsed wall-clock uptime in seconds."""
        return float(time.time() - self._start_time)

    def check_health(
        self,
        deployment_config: Optional[DeploymentConfig] = None,
        platform_config: Optional[SkyVantaConfig] = None,
    ) -> DeploymentHealthContract:
        """Performs a multi-subsystem health evaluation.

        Checks:
        1. Scenario registry catalog availability
        2. Configuration integrity
        3. Hardware isolation compliance (allow_external == False)
        4. Network model download compliance (allow_network_download == False)

        Returns:
            DeploymentHealthContract instance.
        """
        dep_cfg = deployment_config or DeploymentConfig.from_env()
        plat_cfg = platform_config or SkyVantaConfig()

        # 1. Inspect Scenario Registry
        registered_scenarios = ScenarioRegistry.list_all()
        catalog_count = len(registered_scenarios)
        
        sim_status = SimulationStatus.READY if catalog_count > 0 else SimulationStatus.ERROR

        # 2. Verify Safety Invariants
        hardware_isolated = (
            not dep_cfg.allow_external
            and not plat_cfg.flight_interface.safety.allow_external
            and dep_cfg.hardware_disconnected
        )
        network_isolated = (
            not dep_cfg.allow_network_download
            and not plat_cfg.detector.allow_network_download
        )
        safety_enforced = hardware_isolated and network_isolated

        # 3. Aggregate Overall Health State
        if catalog_count >= 10 and safety_enforced:
            status = HealthStatus.HEALTHY
        elif catalog_count > 0:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        return DeploymentHealthContract(
            status=status,
            service="skyvanta-api",
            version=__version__,
            environment=dep_cfg.environment.value,
            uptime_sec=round(self.uptime_sec, 3),
            simulation_engine=sim_status,
            available_scenarios_count=catalog_count,
            hardware_access=not hardware_isolated,
            network_model_download=not network_isolated,
            safety_boundary_enforced=safety_enforced,
            timestamp_sec=time.time(),
        )
