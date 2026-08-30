"""Unit tests for ReleaseVerifier and pre-flight release checks."""

import pytest

from skyvanta.core.config import SkyVantaConfig
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.release.manifest import ReleaseManifest
from skyvanta.deployment.release.verifier import ReleaseVerifier


def test_nominal_release_verification():
    """Verifies that nominal configuration and manifest pass all verification checks."""
    verifier = ReleaseVerifier()
    dep_cfg = DeploymentConfig(environment=DeploymentEnvironment.TESTING)
    plat_cfg = SkyVantaConfig()
    manifest = ReleaseManifest.generate(environment="testing")

    result = verifier.verify(
        deployment_config=dep_cfg,
        platform_config=plat_cfg,
        manifest=manifest,
    )
    assert result.passed is True
    assert len(result.failures) == 0
    assert result.checks["hardware_isolation"] is True
    assert result.checks["network_download_disabled"] is True
    assert result.checks["version_valid"] is True
    assert result.checks["health_service_operational"] is True
    assert result.checks["scenario_registry_available"] is True
    assert result.checks["secret_isolation"] is True


def test_release_verification_fails_on_hardware_access():
    """Verifies that enabling hardware access causes release verification to fail immediately."""
    verifier = ReleaseVerifier()
    dep_cfg = DeploymentConfig()
    # Force bypass to simulate misconfiguration
    dep_cfg.hardware_disconnected = False

    result = verifier.verify(deployment_config=dep_cfg)
    assert result.passed is False
    assert result.checks["hardware_isolation"] is False
    assert any("hardware" in f.lower() for f in result.failures)


def test_release_verification_fails_on_network_download():
    """Verifies that enabling network model downloads causes release verification to fail."""
    verifier = ReleaseVerifier()
    dep_cfg = DeploymentConfig()
    plat_cfg = SkyVantaConfig()
    plat_cfg.detector.allow_network_download = True

    result = verifier.verify(deployment_config=dep_cfg, platform_config=plat_cfg)
    assert result.passed is False
    assert result.checks["network_download_disabled"] is False
    assert any("network" in f.lower() for f in result.failures)


def test_release_verification_fails_on_empty_version():
    """Verifies that missing or blank application version fails verification."""
    verifier = ReleaseVerifier()
    manifest = ReleaseManifest(version="")

    result = verifier.verify(manifest=manifest)
    assert result.passed is False
    assert result.checks["version_valid"] is False
    assert any("version" in f.lower() for f in result.failures)


def test_release_verification_fails_on_secret_leak():
    """Verifies that simulated private keys or raw credentials in metadata trigger security alarms."""
    verifier = ReleaseVerifier()
    manifest = ReleaseManifest(
        git_commit="-----BEGIN RSA PRIVATE KEY-----MIIEowIBAAKCAQEA0...",
    )
    result = verifier.verify(manifest=manifest)
    assert result.passed is False
    assert result.checks["secret_isolation"] is False
    assert any("security" in f.lower() or "secret" in f.lower() for f in result.failures)


def test_release_verification_warning_on_production_without_rate_limit():
    """Verifies that disabled rate limiting in production issues a non-fatal warning."""
    verifier = ReleaseVerifier()
    dep_cfg = DeploymentConfig(
        environment=DeploymentEnvironment.PRODUCTION,
        enable_rate_limiting=False,
    )
    result = verifier.verify(deployment_config=dep_cfg)
    assert any("rate limiting" in w.lower() for w in result.warnings)
