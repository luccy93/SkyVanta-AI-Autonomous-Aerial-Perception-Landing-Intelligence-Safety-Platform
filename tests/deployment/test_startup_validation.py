"""Unit tests for StartupValidator and boot-time invariant verification."""

import pytest

from skyvanta.core.config import SkyVantaConfig
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.reliability.startup import (
    StartupValidationError,
    StartupValidator,
)


def test_nominal_startup_validation():
    """Verifies that nominal startup validation passes all 7 subsystem checks."""
    validator = StartupValidator()
    dep_cfg = DeploymentConfig(environment=DeploymentEnvironment.TESTING)
    plat_cfg = SkyVantaConfig()

    result = validator.validate(
        deployment_config=dep_cfg,
        platform_config=plat_cfg,
    )
    assert result.valid is True
    assert len(result.failures) == 0
    assert result.checks["config_loaded"] is True
    assert result.checks["safety_hardware_isolated"] is True
    assert result.checks["safety_network_download_disabled"] is True
    assert result.checks["scenario_registry_ready"] is True
    assert result.checks["health_subsystem_ready"] is True
    assert result.checks["telemetry_subsystem_ready"] is True
    assert result.checks["security_subsystem_ready"] is True
    assert result.checks["release_manifest_valid"] is True
    assert result.duration_ms >= 0.0


def test_validate_or_raise_nominal():
    """Verifies that validate_or_raise executes without exception on valid configuration."""
    validator = StartupValidator()
    dep_cfg = DeploymentConfig(environment=DeploymentEnvironment.TESTING)
    res = validator.validate_or_raise(deployment_config=dep_cfg)
    assert res.valid is True


def test_startup_validation_fails_on_hardware_access():
    """Verifies that attempting to enable hardware access triggers a StartupValidationError."""
    validator = StartupValidator()
    dep_cfg = DeploymentConfig()
    dep_cfg.hardware_disconnected = False

    result = validator.validate(deployment_config=dep_cfg)
    assert result.valid is False
    assert result.checks["safety_hardware_isolated"] is False

    with pytest.raises(StartupValidationError) as exc_info:
        validator.validate_or_raise(deployment_config=dep_cfg)
    assert "hardware" in str(exc_info.value).lower()


def test_startup_validation_fails_on_network_downloads():
    """Verifies that allowing network model downloads causes startup validation to fail."""
    validator = StartupValidator()
    dep_cfg = DeploymentConfig()
    plat_cfg = SkyVantaConfig()
    plat_cfg.detector.allow_network_download = True

    result = validator.validate(deployment_config=dep_cfg, platform_config=plat_cfg)
    assert result.valid is False
    assert result.checks["safety_network_download_disabled"] is False

    with pytest.raises(StartupValidationError) as exc_info:
        validator.validate_or_raise(deployment_config=dep_cfg, platform_config=plat_cfg)
    assert "download" in str(exc_info.value).lower()


def test_startup_validation_fails_on_missing_scenarios(monkeypatch):
    """Verifies that empty scenario catalog halts startup."""
    validator = StartupValidator()
    from skyvanta.simulation.registry import ScenarioRegistry

    # Mock empty registry
    monkeypatch.setattr(ScenarioRegistry, "list_all", lambda: [])

    result = validator.validate()
    assert result.valid is False
    assert result.checks["scenario_registry_ready"] is False

    with pytest.raises(StartupValidationError):
        validator.validate_or_raise()
