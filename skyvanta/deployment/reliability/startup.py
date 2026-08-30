"""Startup validation, pre-flight invariant verification, and fail-safe boot checks."""

import logging
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from skyvanta.core.config import SkyVantaConfig
from skyvanta.core.exceptions import SkyVantaError
from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.health import HealthCheckService
from skyvanta.deployment.release.verifier import ReleaseVerifier
from skyvanta.deployment.security.api_keys import api_key_manager
from skyvanta.deployment.security.rate_limit import rate_limiter
from skyvanta.simulation.registry import ScenarioRegistry

logger = logging.getLogger("skyvanta.reliability.startup")


class StartupValidationError(SkyVantaError):
    """Raised when mandatory startup validation or safety invariants fail."""


class StartupValidationResult(BaseModel):
    """Result model containing diagnostic details from startup validation."""

    valid: bool = Field(
        description="Whether all startup validations succeeded.",
    )
    checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="Dictionary mapping validation check names to boolean pass status.",
    )
    failures: List[str] = Field(
        default_factory=list,
        description="List of critical failure reasons.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of non-fatal operational warnings.",
    )
    duration_ms: float = Field(
        default=0.0,
        description="Elapsed validation time in milliseconds.",
    )


class StartupValidator:
    """Validates pre-flight conditions before the application accepts traffic."""

    def __init__(self):
        self._health_service = HealthCheckService()
        self._release_verifier = ReleaseVerifier()

    def validate(
        self,
        deployment_config: Optional[DeploymentConfig] = None,
        platform_config: Optional[SkyVantaConfig] = None,
    ) -> StartupValidationResult:
        """Executes full multi-subsystem startup verification.

        Verification Steps:
        1. Configuration loads & validation
        2. Safety flags & hardware isolation enforcement
        3. Scenario registry catalog availability
        4. Health subsystem initialization
        5. Telemetry subsystem initialization
        6. Security subsystem initialization
        7. Release manifest integrity

        Returns:
            StartupValidationResult instance.
        """
        start_time = time.perf_counter()
        checks: Dict[str, bool] = {}
        failures: List[str] = []
        warnings: List[str] = []

        try:
            dep_cfg = deployment_config or DeploymentConfig.from_env()
            checks["config_loaded"] = True
        except Exception as e:
            checks["config_loaded"] = False
            failures.append(f"Configuration failed to load: {e}")
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return StartupValidationResult(
                valid=False,
                checks=checks,
                failures=failures,
                warnings=warnings,
                duration_ms=round(elapsed_ms, 2),
            )

        plat_cfg = platform_config or SkyVantaConfig()

        # 1. Safety flags and hardware isolation
        hw_safe = (
            not dep_cfg.allow_external
            and not plat_cfg.flight_interface.safety.allow_external
            and dep_cfg.hardware_disconnected
        )
        checks["safety_hardware_isolated"] = hw_safe
        if not hw_safe:
            failures.append("Safety Violation: Hardware access or external actuation is enabled.")

        net_safe = (
            not dep_cfg.allow_network_download
            and not plat_cfg.detector.allow_network_download
        )
        checks["safety_network_download_disabled"] = net_safe
        if not net_safe:
            failures.append("Safety Violation: Runtime network model downloads are enabled.")

        # 2. Scenario registry catalog
        try:
            scenarios = ScenarioRegistry.list_all()
            scen_count = len(scenarios)
            scen_ok = scen_count >= 10
            checks["scenario_registry_ready"] = scen_ok
            if not scen_ok:
                failures.append(f"Scenario registry has insufficient scenarios ({scen_count} < 10).")
        except Exception as e:
            checks["scenario_registry_ready"] = False
            failures.append(f"Scenario registry inspection failed: {e}")

        # 3. Health subsystem
        try:
            health = self._health_service.check_health(
                deployment_config=dep_cfg,
                platform_config=plat_cfg,
            )
            health_ok = health.safety_boundary_enforced and health.status.value in ("healthy", "degraded")
            checks["health_subsystem_ready"] = health_ok
            if not health_ok:
                failures.append(f"Health subsystem check failed with status '{health.status.value}'.")
        except Exception as e:
            checks["health_subsystem_ready"] = False
            failures.append(f"Health subsystem failed to initialize: {e}")

        # 4. Telemetry subsystem
        try:
            from skyvanta.deployment.api.services.telemetry_service import TelemetryService
            # Test instantiation
            _ = TelemetryService()
            checks["telemetry_subsystem_ready"] = True
        except Exception as e:
            checks["telemetry_subsystem_ready"] = False
            failures.append(f"Telemetry subsystem failed to initialize: {e}")

        # 5. Security subsystem
        try:
            keys_ok = api_key_manager is not None
            limiter_ok = rate_limiter is not None
            sec_ok = keys_ok and limiter_ok
            checks["security_subsystem_ready"] = sec_ok
            if not sec_ok:
                failures.append("Security subsystem (API key manager or rate limiter) not initialized.")
        except Exception as e:
            checks["security_subsystem_ready"] = False
            failures.append(f"Security subsystem failed to initialize: {e}")

        # 6. Release manifest & verifier
        try:
            rel_res = self._release_verifier.verify(
                deployment_config=dep_cfg,
                platform_config=plat_cfg,
            )
            checks["release_manifest_valid"] = rel_res.passed
            if not rel_res.passed:
                failures.extend(rel_res.failures)
            warnings.extend(rel_res.warnings)
        except Exception as e:
            checks["release_manifest_valid"] = False
            failures.append(f"Release manifest verification failed: {e}")

        is_valid = (len(failures) == 0) and all(checks.values())
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return StartupValidationResult(
            valid=is_valid,
            checks=checks,
            failures=failures,
            warnings=warnings,
            duration_ms=round(elapsed_ms, 2),
        )

    def validate_or_raise(
        self,
        deployment_config: Optional[DeploymentConfig] = None,
        platform_config: Optional[SkyVantaConfig] = None,
    ) -> StartupValidationResult:
        """Executes startup validation and raises StartupValidationError on failure."""
        result = self.validate(
            deployment_config=deployment_config,
            platform_config=platform_config,
        )
        if not result.valid:
            error_details = "; ".join(result.failures)
            logger.critical("Startup validation failed: %s", error_details)
            raise StartupValidationError(
                f"Application startup failed safety or invariant checks: {error_details}"
            )
        return result
