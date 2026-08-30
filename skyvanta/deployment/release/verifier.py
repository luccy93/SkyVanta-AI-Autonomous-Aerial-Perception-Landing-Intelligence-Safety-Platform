"""Release verification engine, pre-flight safety checks, and security audit verifier."""

import os
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from skyvanta.core.config import SkyVantaConfig
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.health import HealthCheckService
from skyvanta.deployment.release.manifest import ReleaseManifest
from skyvanta.simulation.registry import ScenarioRegistry


class ReleaseVerificationResult(BaseModel):
    """Strongly typed result container for release pre-flight verification."""

    passed: bool = Field(
        description="Whether all mandatory release verification checks passed.",
    )
    checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="Mapping of individual check names to boolean pass/fail status.",
    )
    failures: List[str] = Field(
        default_factory=list,
        description="List of critical invariant check failure descriptions.",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="List of non-blocking operational warnings.",
    )
    timestamp_sec: float = Field(
        default_factory=lambda: time.time(),
        description="Unix timestamp when verification was conducted.",
    )
    manifest: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Sanitized release manifest metadata snapshot.",
    )


class ReleaseVerifier:
    """Evaluates software release readiness, safety boundaries, and credential isolation."""

    # Patterns indicating potential secret leakage
    _SECRET_PATTERNS = [
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
        re.compile(r"sk_live_[0-9a-zA-Z]{16,}"),
        re.compile(r"sk_test_[0-9a-zA-Z]{16,}"),
        re.compile(r"password\s*[:=]\s*['\"][^\s'\"]+['\"]", re.IGNORECASE),
        re.compile(r"api_key\s*[:=]\s*['\"][^\s'\"]{10,}['\"]", re.IGNORECASE),
    ]

    def __init__(self):
        self._health_service = HealthCheckService()

    def verify(
        self,
        deployment_config: Optional[DeploymentConfig] = None,
        platform_config: Optional[SkyVantaConfig] = None,
        manifest: Optional[ReleaseManifest] = None,
    ) -> ReleaseVerificationResult:
        """Executes a full multi-dimensional pre-flight release verification.

        Checks:
        1. Configuration safety invariants (allow_external=False, allow_network_download=False, hardware_disconnected=True)
        2. Application metadata integrity (version, api_version, environment)
        3. Runtime dependencies (health check service, scenario catalog >= 10)
        4. Security sanitization (no leaked keys, tokens, or private keys)

        Returns:
            ReleaseVerificationResult instance.
        """
        dep_cfg = deployment_config or DeploymentConfig.from_env()
        plat_cfg = platform_config or SkyVantaConfig()
        rel_manifest = manifest or ReleaseManifest.generate(
            environment=dep_cfg.environment.value,
            base_dir=os.getcwd(),
        )

        checks: Dict[str, bool] = {}
        failures: List[str] = []
        warnings: List[str] = []

        # ----------------------------------------------------------------------
        # 1. Configuration & Safety Invariants
        # ----------------------------------------------------------------------
        hw_isolated = (
            not dep_cfg.allow_external
            and not plat_cfg.flight_interface.safety.allow_external
            and dep_cfg.hardware_disconnected
        )
        checks["hardware_isolation"] = hw_isolated
        if not hw_isolated:
            failures.append("Safety Invariant Violated: hardware_access is active or hardware is not disconnected.")

        network_isolated = (
            not dep_cfg.allow_network_download
            and not plat_cfg.detector.allow_network_download
        )
        checks["network_download_disabled"] = network_isolated
        if not network_isolated:
            failures.append("Safety Invariant Violated: allow_network_download is True.")

        safety_flags_consistent = (
            not rel_manifest.hardware_access
            and not rel_manifest.network_model_download
        )
        checks["manifest_safety_invariants"] = safety_flags_consistent
        if not safety_flags_consistent:
            failures.append("Release Manifest shows hardware_access or network_model_download enabled.")

        # ----------------------------------------------------------------------
        # 2. Application & Version Integrity
        # ----------------------------------------------------------------------
        version_valid = bool(rel_manifest.version and len(rel_manifest.version.strip()) > 0)
        checks["version_valid"] = version_valid
        if not version_valid:
            failures.append("Application release version is missing or empty.")

        api_version_valid = bool(rel_manifest.api_version and len(rel_manifest.api_version.strip()) > 0)
        checks["api_version_valid"] = api_version_valid
        if not api_version_valid:
            failures.append("API version specification is missing or empty.")

        env_valid = dep_cfg.environment in [
            DeploymentEnvironment.DEVELOPMENT,
            DeploymentEnvironment.TESTING,
            DeploymentEnvironment.PRODUCTION,
        ]
        checks["environment_valid"] = env_valid
        if not env_valid:
            failures.append(f"Invalid deployment environment: '{dep_cfg.environment}'.")

        if dep_cfg.environment == DeploymentEnvironment.PRODUCTION and dep_cfg.debug:
            checks["production_debug_disabled"] = False
            failures.append("Production environment has debug mode enabled.")
        else:
            checks["production_debug_disabled"] = True

        # ----------------------------------------------------------------------
        # 3. Runtime & Subsystem Readiness
        # ----------------------------------------------------------------------
        health_contract = self._health_service.check_health(
            deployment_config=dep_cfg,
            platform_config=plat_cfg,
        )
        health_ok = health_contract.safety_boundary_enforced and health_contract.status.value in ("healthy", "degraded")
        checks["health_service_operational"] = health_ok
        if not health_ok:
            failures.append(f"Health service check failed (Status: {health_contract.status.value}).")

        registered_scenarios = ScenarioRegistry.list_all()
        scenario_count = len(registered_scenarios)
        scenario_catalog_ok = scenario_count >= 10
        checks["scenario_registry_available"] = scenario_catalog_ok
        if not scenario_catalog_ok:
            failures.append(f"Scenario registry contains insufficient scenarios ({scenario_count} < 10).")

        # ----------------------------------------------------------------------
        # 4. Security & Secret Redaction Audit
        # ----------------------------------------------------------------------
        manifest_dump = rel_manifest.to_json()
        secret_detected = False
        for pattern in self._SECRET_PATTERNS:
            if pattern.search(manifest_dump):
                secret_detected = True
                break

        checks["secret_isolation"] = not secret_detected
        if secret_detected:
            failures.append("Security Alert: Sensitive credential or private key detected in release metadata.")

        # Rate limiting check in production
        if dep_cfg.environment == DeploymentEnvironment.PRODUCTION and not dep_cfg.enable_rate_limiting:
            warnings.append("Rate limiting is disabled in a production configuration.")

        # Determine overall pass
        passed = (len(failures) == 0) and all(checks.values())

        return ReleaseVerificationResult(
            passed=passed,
            checks=checks,
            failures=failures,
            warnings=warnings,
            timestamp_sec=time.time(),
            manifest=rel_manifest.to_dict(),
        )
