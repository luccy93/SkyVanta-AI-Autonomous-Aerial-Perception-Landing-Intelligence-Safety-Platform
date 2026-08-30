"""Unit tests for system runtime monitoring and resource warning thresholds."""

import os
from unittest.mock import patch
from skyvanta.deployment.observability.runtime import SystemResourceMonitor


def test_system_resource_monitor_metrics():
    """SystemResourceMonitor must return valid system resource metrics without crashing."""
    monitor = SystemResourceMonitor()
    usage = monitor.get_resource_usage()

    assert "uptime_sec" in usage
    assert usage["uptime_sec"] >= 0.0
    assert "cpu_percent" in usage
    assert usage["cpu_percent"] >= 0.0
    assert "memory_rss_mb" in usage
    assert usage["memory_rss_mb"] >= 0.0
    assert "python_version" in usage
    assert "application_version" in usage
    assert "api_version" in usage
    assert usage["api_version"] == "v1"
    assert "git_commit" in usage
    assert "build_timestamp" in usage


def test_system_resource_monitor_git_commit_env():
    """Git commit resolution must prioritize environment variables."""
    monitor = SystemResourceMonitor()
    with patch.dict(os.environ, {"GIT_COMMIT": "abc123def4567890abcdef1234567890abcdef12"}):
        monitor._cached_git_commit = None
        commit = monitor.get_git_commit()
        assert commit == "abc123def4567890abcdef1234567890abcdef12"


def test_system_resource_monitor_warning_thresholds():
    """SystemResourceMonitor must identify threshold breaches as diagnostic warnings."""
    monitor = SystemResourceMonitor()

    # Case 1: Normal operating parameters (no warnings)
    with patch.object(monitor, "get_resource_usage", return_value={"cpu_percent": 15.0, "memory_rss_mb": 128.0}):
        warnings = monitor.evaluate_warnings(
            cpu_threshold_pct=85.0,
            memory_threshold_mb=512.0,
            max_ws_clients=50,
            active_ws_clients=5,
            ws_warning_pct=80.0,
        )
        assert len(warnings) == 0

    # Case 2: CPU breach
    with patch.object(monitor, "get_resource_usage", return_value={"cpu_percent": 92.5, "memory_rss_mb": 200.0}):
        warnings = monitor.evaluate_warnings(
            cpu_threshold_pct=85.0,
            memory_threshold_mb=512.0,
            max_ws_clients=50,
            active_ws_clients=5,
            ws_warning_pct=80.0,
        )
        assert len(warnings) == 1
        assert "CPU usage (92.5%)" in warnings[0]

    # Case 3: Memory breach
    with patch.object(monitor, "get_resource_usage", return_value={"cpu_percent": 30.0, "memory_rss_mb": 650.0}):
        warnings = monitor.evaluate_warnings(
            cpu_threshold_pct=85.0,
            memory_threshold_mb=512.0,
            max_ws_clients=50,
            active_ws_clients=5,
            ws_warning_pct=80.0,
        )
        assert len(warnings) == 1
        assert "Memory RSS (650.0 MB)" in warnings[0]

    # Case 4: WebSocket capacity warning
    with patch.object(monitor, "get_resource_usage", return_value={"cpu_percent": 10.0, "memory_rss_mb": 100.0}):
        warnings = monitor.evaluate_warnings(
            cpu_threshold_pct=85.0,
            memory_threshold_mb=512.0,
            max_ws_clients=50,
            active_ws_clients=45,
            ws_warning_pct=80.0,
        )
        assert len(warnings) == 1
        assert "Active WebSocket connections (45/50, 90.0%)" in warnings[0]
