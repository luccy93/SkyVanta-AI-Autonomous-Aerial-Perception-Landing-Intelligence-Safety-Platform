"""Unit tests for SkyVanta AI deployment boundary, health contracts, and environment configurations."""

import json
import logging
import os
import pytest

from skyvanta.core.config import SkyVantaConfig
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.contracts import (
    DeploymentHealthContract,
    HealthStatus,
    ScenarioRunRequest,
    ScenarioRunResponse,
    SimulationStatus,
    TelemetryStreamPacket,
)
from skyvanta.deployment.health import HealthCheckService
from skyvanta.deployment.logging import DeploymentLogger, JSONDeploymentFormatter


class TestDeploymentConfiguration:
    """Verifies deployment configuration parsing, defaults, and safety invariants."""

    def test_deployment_config_defaults(self):
        """Default configuration must strictly enforce hardware and network isolation."""
        config = DeploymentConfig()
        assert config.environment == DeploymentEnvironment.DEVELOPMENT
        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.log_level == "INFO"
        assert config.allow_external is False
        assert config.allow_network_download is False
        assert config.hardware_disconnected is True

    def test_deployment_config_from_env(self, monkeypatch):
        """Environment variables must be parsed correctly while preserving safety defaults."""
        monkeypatch.setenv("SKYVANTA_ENV", "production")
        monkeypatch.setenv("SKYVANTA_HOST", "127.0.0.1")
        monkeypatch.setenv("SKYVANTA_PORT", "9090")
        monkeypatch.setenv("SKYVANTA_LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("SKYVANTA_CORS_ORIGINS", "http://app.skyvanta.internal,http://localhost:3000")
        monkeypatch.setenv("SKYVANTA_TELEMETRY_RATE_HZ", "30.0")

        config = DeploymentConfig.from_env()
        assert config.environment == DeploymentEnvironment.PRODUCTION
        assert config.host == "127.0.0.1"
        assert config.port == 9090
        assert config.log_level == "DEBUG"
        assert len(config.cors_origins) == 2
        assert "http://app.skyvanta.internal" in config.cors_origins
        assert config.telemetry_rate_hz == 30.0
        # Safety invariants remain strictly false/true
        assert config.allow_external is False
        assert config.allow_network_download is False
        assert config.hardware_disconnected is True


class TestDeploymentHealthContract:
    """Verifies health inspection service and contract serialization."""

    def test_health_check_service_nominal(self):
        """Health service must report HEALTHY when all scenarios and safety invariants are intact."""
        service = HealthCheckService()
        health = service.check_health()

        assert health.status == HealthStatus.HEALTHY
        assert health.service == "skyvanta-api"
        assert health.simulation_engine == SimulationStatus.READY
        assert health.available_scenarios_count >= 10
        assert health.hardware_access is False
        assert health.network_model_download is False
        assert health.safety_boundary_enforced is True
        assert health.uptime_sec >= 0.0

    def test_health_contract_json_serialization(self):
        """Health contract must serialize to a valid JSON dictionary conforming to schema."""
        service = HealthCheckService()
        health = service.check_health()
        json_data = json.loads(health.model_dump_json())

        assert json_data["status"] == "healthy"
        assert json_data["service"] == "skyvanta-api"
        assert json_data["hardware_access"] is False
        assert json_data["network_model_download"] is False
        assert json_data["safety_boundary_enforced"] is True
        assert "uptime_sec" in json_data
        assert "timestamp_sec" in json_data

    def test_scenario_run_contracts(self):
        """Scenario request and response data contracts must validate types properly."""
        req = ScenarioRunRequest(scenario_name="nominal_landing", seed=123)
        assert req.scenario_name == "nominal_landing"
        assert req.seed == 123

        resp = ScenarioRunResponse(
            run_id="run_test_01",
            scenario_name="nominal_landing",
            status="SUCCESS_LANDED",
            seed=123,
            duration_sim_sec=15.85,
            duration_wall_sec=0.48,
            realtime_factor=33.0,
            final_position_error_m=0.01,
            rmse_position_m=0.014,
            safety_violations_count=0,
            is_success=True,
        )
        assert resp.is_success is True
        assert resp.safety_violations_count == 0

    def test_telemetry_stream_packet(self):
        """Telemetry WebSocket packet schema must validate coordinate arrays and flags."""
        packet = TelemetryStreamPacket(
            timestamp_sim_sec=1.5,
            position_m=[0.1, -0.2, 5.4],
            velocity_m_s=[0.0, 0.0, -0.5],
            attitude_rpy_deg=[1.2, -0.8, 45.0],
            landing_phase="DESCENDING",
            recommended_action="CONTINUE_DESCENT",
            target_visible=True,
            position_uncertainty_3sigma_m=0.035,
            is_safe=True,
        )
        assert packet.position_m == [0.1, -0.2, 5.4]
        assert packet.is_safe is True


class TestDeploymentLogging:
    """Verifies structured deployment logging and JSON formatting."""

    def test_json_formatter_structure(self):
        """JSONDeploymentFormatter must produce parseable JSON with timestamp, level, and message."""
        formatter = JSONDeploymentFormatter()
        record = logging.LogRecord(
            name="skyvanta.deployment",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Simulation service initialized",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "skyvanta.deployment"
        assert parsed["message"] == "Simulation service initialized"
        assert parsed["service"] == "skyvanta-deployment"
        assert "timestamp" in parsed

    def test_deployment_logger_configuration(self):
        """DeploymentLogger must configure stdout handler and logging level."""
        logger = DeploymentLogger.configure_logging(level="DEBUG", json_format=False)
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) >= 1
