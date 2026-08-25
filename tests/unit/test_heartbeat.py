"""Unit tests for HeartbeatMonitor."""

import pytest
from skyvanta.core.config import HeartbeatConfig
from skyvanta.core.types import AutopilotHealthStatus
from skyvanta.flight.health import HeartbeatMonitor


def test_heartbeat_healthy_state():
    """Verifies that fresh heartbeats yield HEALTHY status."""
    monitor = HeartbeatMonitor(HeartbeatConfig(expected_interval_sec=1.0, timeout_sec=2.5))
    monitor.record_heartbeat(timestamp_sec=10.0)

    health = monitor.check_health(current_time_sec=10.5)
    assert health.connected is True
    assert health.health_status == AutopilotHealthStatus.HEALTHY
    assert health.failure_reason is None


def test_heartbeat_degraded_state():
    """Verifies that moderately delayed heartbeat produces DEGRADED status."""
    monitor = HeartbeatMonitor(HeartbeatConfig(expected_interval_sec=1.0, timeout_sec=2.5))
    monitor.record_heartbeat(timestamp_sec=10.0)

    health = monitor.check_health(current_time_sec=11.8)  # > 1.5s delay
    assert health.connected is True
    assert health.health_status == AutopilotHealthStatus.DEGRADED
    assert "delayed" in health.failure_reason.lower()


def test_heartbeat_timeout_disconnected_state():
    """Verifies that exceeding timeout produces DISCONNECTED status."""
    monitor = HeartbeatMonitor(HeartbeatConfig(expected_interval_sec=1.0, timeout_sec=2.5))
    monitor.record_heartbeat(timestamp_sec=10.0)

    health = monitor.check_health(current_time_sec=13.0)  # > 2.5s timeout
    assert health.connected is False
    assert health.health_status == AutopilotHealthStatus.DISCONNECTED
    assert "timeout" in health.failure_reason.lower()
