"""Unit tests for bounded cardinality operational metrics and latency stats."""

import time
import pytest
from skyvanta.deployment.observability.metrics import (
    LatencyStats,
    MetricsCollector,
    RouteNormalizer,
    ScenarioMetricRecord,
)


def test_route_normalizer_known_and_bounded_cardinality():
    """RouteNormalizer must map arbitrary user URLs to bounded templates."""
    assert RouteNormalizer.normalize("/health") == "/health"
    assert RouteNormalizer.normalize("/ready") == "/ready"
    assert RouteNormalizer.normalize("/api/v1/system/info") == "/api/v1/system/info"
    assert RouteNormalizer.normalize("/api/v1/metrics") == "/api/v1/metrics"
    assert RouteNormalizer.normalize("/api/v1/scenarios") == "/api/v1/scenarios"
    assert RouteNormalizer.normalize("/api/v1/scenarios/run") == "/api/v1/scenarios/run"
    assert RouteNormalizer.normalize("/api/v1/scenarios/nominal_landing") == "/api/v1/scenarios/{scenario_name}"
    assert RouteNormalizer.normalize("/api/v1/scenarios/arbitrary_custom_name_12345") == "/api/v1/scenarios/{scenario_name}"
    assert RouteNormalizer.normalize("/api/v1/telemetry/ws") == "/api/v1/telemetry/ws"
    
    # Query parameters must be stripped
    assert RouteNormalizer.normalize("/api/v1/telemetry/ws?scenario=nominal_landing&rate_hz=20") == "/api/v1/telemetry/ws"

    # Arbitrary high-cardinality attacker paths must map to 'other'
    assert RouteNormalizer.normalize("/attacker/path/12345") == "other"
    assert RouteNormalizer.normalize("/unknown/random/guid/987654") == "other"
    assert RouteNormalizer.normalize("") == "other"


def test_latency_stats_exact_percentiles():
    """LatencyStats must calculate exact min, mean, median, p95, p99, max."""
    # Empty samples
    empty_res = LatencyStats.calculate([])
    assert empty_res["min_ms"] == 0.0
    assert empty_res["avg_ms"] == 0.0
    assert empty_res["median_ms"] == 0.0
    assert empty_res["p95_ms"] == 0.0
    assert empty_res["p99_ms"] == 0.0
    assert empty_res["max_ms"] == 0.0
    assert empty_res["sample_count"] == 0

    # 100 deterministic values 1.0 ... 100.0
    latencies = [float(i) for i in range(1, 101)]
    res = LatencyStats.calculate(latencies)
    assert res["min_ms"] == 1.0
    assert res["max_ms"] == 100.0
    assert res["avg_ms"] == 50.5
    assert res["median_ms"] == 50.5
    assert res["p95_ms"] == 95.05
    assert res["p99_ms"] == 99.01
    assert res["sample_count"] == 100


def test_metrics_collector_http_and_error_recording():
    """MetricsCollector must record requests, methods, statuses, and errors accurately."""
    collector = MetricsCollector(latency_window_size=100)
    collector.reset()

    collector.record_http_request("GET", "/health", 200, 1.5, is_slow=False)
    collector.record_http_request("GET", "/health", 200, 2.0, is_slow=False)
    collector.record_http_request("POST", "/api/v1/scenarios/run", 200, 150.0, is_slow=False)
    collector.record_http_request("POST", "/api/v1/scenarios/run", 400, 5.0, is_slow=False)
    collector.record_http_request("GET", "/api/v1/scenarios/run", 500, 1200.0, is_slow=True)

    collector.record_error("validation")
    collector.record_error("scenario")
    collector.record_error("internal")
    collector.record_error("websocket")

    http = collector.get_http_metrics()
    assert http["total_requests"] == 5
    assert http["successful_requests"] == 3
    assert http["failed_requests"] == 2
    assert http["slow_requests"] == 1
    assert http["requests_by_method"]["GET"] == 3
    assert http["requests_by_method"]["POST"] == 2
    assert http["requests_by_status"][200] == 3
    assert http["requests_by_status"][400] == 1
    assert http["requests_by_status"][500] == 1
    assert http["latency_overall"]["sample_count"] == 5
    assert http["latency_overall"]["max_ms"] == 1200.0

    errors = collector.get_error_metrics()
    assert errors["validation_errors"] == 1
    assert errors["scenario_execution_failures"] == 1
    assert errors["internal_errors"] == 1
    assert errors["websocket_errors"] == 1
    assert errors["total_errors"] == 4


def test_metrics_collector_websocket_metrics():
    """MetricsCollector must track WebSocket connections, durations, and rates."""
    collector = MetricsCollector()
    collector.reset()

    collector.set_ws_configured_rate(30.0)
    collector.record_ws_connect()
    collector.record_ws_connect()
    assert collector.ws_active_connections == 2
    assert collector.ws_total_connections == 2

    collector.record_ws_packet_sent(10)
    collector.record_ws_packet_dropped(2)
    collector.record_ws_heartbeat_failure()

    collector.record_ws_disconnect(12.5)
    assert collector.ws_active_connections == 1
    assert collector.ws_disconnects == 1

    ws = collector.get_websocket_metrics()
    assert ws["active_connections"] == 1
    assert ws["total_connections"] == 2
    assert ws["disconnects"] == 1
    assert ws["telemetry_packets_sent"] == 10
    assert ws["dropped_packets"] == 2
    assert ws["heartbeat_failures"] == 1
    assert ws["configured_stream_rate_hz"] == 30.0
    assert ws["duration_stats"]["avg_sec"] == 12.5


def test_metrics_collector_scenario_execution_tracking():
    """MetricsCollector must aggregate scenario run statistics and safety decisions."""
    collector = MetricsCollector()
    collector.reset()

    collector.record_scenario_run(
        scenario_name="nominal_landing",
        is_success=True,
        duration_wall_sec=0.25,
        realtime_factor=80.0,
        final_position_error_m=0.035,
        decision_status="SUCCESS_LANDED",
    )
    collector.record_scenario_run(
        scenario_name="nominal_landing",
        is_success=True,
        duration_wall_sec=0.23,
        realtime_factor=85.0,
        final_position_error_m=0.040,
        decision_status="SUCCESS_LANDED",
    )
    collector.record_scenario_run(
        scenario_name="high_wind_landing",
        is_success=False,
        duration_wall_sec=0.30,
        realtime_factor=60.0,
        final_position_error_m=0.250,
        decision_status="ABORTED",
    )

    scenarios = collector.get_scenario_metrics()
    assert scenarios["total_executions"] == 3
    assert scenarios["successful_executions"] == 2
    assert scenarios["failed_executions"] == 1
    
    nom = scenarios["scenarios"]["nominal_landing"]
    assert nom["executions"] == 2
    assert nom["successful_executions"] == 2
    assert nom["failed_executions"] == 0
    assert nom["decisions_breakdown"]["SUCCESS_LANDED"] == 2
    assert 0.035 <= nom["avg_final_position_error_m"] <= 0.040

    wind = scenarios["scenarios"]["high_wind_landing"]
    assert wind["executions"] == 1
    assert wind["failed_executions"] == 1
    assert wind["decisions_breakdown"]["ABORTED"] == 1


def test_metrics_collector_bounded_memory():
    """MetricsCollector deques must not grow unbounded beyond configured maxlen."""
    window_size = 50
    collector = MetricsCollector(latency_window_size=window_size)
    collector.reset()

    # Record 200 items into window of size 50
    for i in range(200):
        collector.record_http_request("GET", "/health", 200, float(i))

    assert len(collector._overall_latencies_ms) == window_size
    http = collector.get_http_metrics()
    assert http["latency_overall"]["sample_count"] == window_size
    assert http["total_requests"] == 200
