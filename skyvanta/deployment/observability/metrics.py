"""Bounded cardinality operational metrics collector and latency analyzer."""

from collections import defaultdict, deque
import threading
import time
from typing import Any, Deque, Dict, List, Optional
import numpy as np


class RouteNormalizer:
    """Normalizes arbitrary HTTP request paths into bounded cardinality route patterns."""

    KNOWN_PATTERNS = [
        ("/", "/"),
        ("/health", "/health"),
        ("/ready", "/ready"),
        ("/docs", "/docs"),
        ("/redoc", "/redoc"),
        ("/openapi.json", "/openapi.json"),
        ("/api/v1/system/info", "/api/v1/system/info"),
        ("/api/v1/metrics", "/api/v1/metrics"),
        ("/api/v1/scenarios/run", "/api/v1/scenarios/run"),
        ("/api/v1/scenarios", "/api/v1/scenarios"),
        ("/api/v1/telemetry/ws", "/api/v1/telemetry/ws"),
    ]

    @classmethod
    def normalize(cls, path: str) -> str:
        """Maps an incoming raw URL path to a bounded route template."""
        if not path:
            return "other"
        
        clean = path.split("?")[0].rstrip("/")
        if not clean:
            return "/"

        for pattern, route in cls.KNOWN_PATTERNS:
            if clean == pattern:
                return route

        if clean.startswith("/api/v1/scenarios/"):
            return "/api/v1/scenarios/{scenario_name}"

        return "other"


class LatencyStats:
    """Calculates summary and percentile statistics over a bounded sliding window of timings."""

    @staticmethod
    def calculate(latencies_ms: List[float]) -> Dict[str, float]:
        """Calculates min, avg, median, p95, p99, and max from a list of latencies in ms."""
        if not latencies_ms:
            return {
                "min_ms": 0.0,
                "avg_ms": 0.0,
                "median_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "max_ms": 0.0,
                "sample_count": 0,
            }

        arr = np.array(latencies_ms, dtype=np.float64)
        return {
            "min_ms": round(float(np.min(arr)), 3),
            "avg_ms": round(float(np.mean(arr)), 3),
            "median_ms": round(float(np.percentile(arr, 50)), 3),
            "p95_ms": round(float(np.percentile(arr, 95)), 3),
            "p99_ms": round(float(np.percentile(arr, 99)), 3),
            "max_ms": round(float(np.max(arr)), 3),
            "sample_count": len(latencies_ms),
        }


class ScenarioMetricRecord:
    """Tracks execution performance for a specific benchmark scenario."""

    def __init__(self, name: str, maxlen: int = 100):
        self.name = name
        self.executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        self.duration_wall_sec: Deque[float] = deque(maxlen=maxlen)
        self.realtime_factors: Deque[float] = deque(maxlen=maxlen)
        self.final_position_errors_m: Deque[float] = deque(maxlen=maxlen)
        self.decisions: Dict[str, int] = defaultdict(int)

    def record(
        self,
        is_success: bool,
        duration_wall_sec: float,
        realtime_factor: float,
        final_position_error_m: float,
        decision_status: str,
    ) -> None:
        """Records a completed scenario execution."""
        self.executions += 1
        if is_success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1

        self.duration_wall_sec.append(duration_wall_sec)
        self.realtime_factors.append(realtime_factor)
        self.final_position_errors_m.append(final_position_error_m)
        self.decisions[str(decision_status)] += 1

    def to_dict(self) -> Dict[str, Any]:
        """Summarizes scenario execution metrics."""
        durations = list(self.duration_wall_sec)
        rtfs = list(self.realtime_factors)
        pos_errors = list(self.final_position_errors_m)

        return {
            "name": self.name,
            "executions": self.executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "avg_duration_wall_sec": round(float(np.mean(durations)), 3) if durations else 0.0,
            "min_duration_wall_sec": round(float(np.min(durations)), 3) if durations else 0.0,
            "max_duration_wall_sec": round(float(np.max(durations)), 3) if durations else 0.0,
            "avg_realtime_factor": round(float(np.mean(rtfs)), 2) if rtfs else 0.0,
            "avg_final_position_error_m": round(float(np.mean(pos_errors)), 4) if pos_errors else 0.0,
            "decisions_breakdown": dict(self.decisions),
        }


class MetricsCollector:
    """Centralized, bounded in-memory metrics registry for HTTP, WebSocket, and Scenario execution."""

    def __init__(self, latency_window_size: int = 1000):
        self._lock = threading.RLock()
        self.latency_window_size = latency_window_size

        # HTTP Request Metrics
        self.total_requests = 0
        self.requests_by_method: Dict[str, int] = defaultdict(int)
        self.requests_by_endpoint: Dict[str, int] = defaultdict(int)
        self.successful_requests = 0
        self.failed_requests = 0
        self.requests_by_status: Dict[int, int] = defaultdict(int)
        self.slow_requests = 0

        # Latencies (Rolling deques)
        self._overall_latencies_ms: Deque[float] = deque(maxlen=latency_window_size)
        self._route_latencies_ms: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=min(200, latency_window_size))
        )

        # Error Metrics
        self.validation_errors = 0
        self.scenario_execution_failures = 0
        self.internal_errors = 0
        self.websocket_errors = 0
        self.config_failures = 0
        self.startup_failures = 0

        # WebSocket Metrics
        self.ws_active_connections = 0
        self.ws_total_connections = 0
        self.ws_disconnects = 0
        self.ws_telemetry_packets_sent = 0
        self.ws_dropped_packets = 0
        self.ws_heartbeat_failures = 0
        self.ws_reconnect_events = 0
        self.ws_durations_sec: Deque[float] = deque(maxlen=500)
        self.ws_configured_stream_rate_hz = 20.0
        self._ws_packet_timestamps: Deque[float] = deque(maxlen=1000)

        # Scenario Metrics (keyed by scenario name)
        self._scenarios: Dict[str, ScenarioMetricRecord] = {}

    def record_http_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        is_slow: bool = False,
    ) -> None:
        """Records an incoming HTTP request and latency."""
        norm_route = RouteNormalizer.normalize(path)
        m_upper = method.upper()

        with self._lock:
            self.total_requests += 1
            self.requests_by_method[m_upper] += 1
            self.requests_by_endpoint[norm_route] += 1
            self.requests_by_status[status_code] += 1

            if status_code < 400:
                self.successful_requests += 1
            else:
                self.failed_requests += 1

            if is_slow:
                self.slow_requests += 1

            self._overall_latencies_ms.append(duration_ms)
            self._route_latencies_ms[norm_route].append(duration_ms)

    def record_error(self, error_category: str) -> None:
        """Increments a specific categorized error counter."""
        with self._lock:
            if error_category == "validation":
                self.validation_errors += 1
            elif error_category == "scenario":
                self.scenario_execution_failures += 1
            elif error_category == "internal":
                self.internal_errors += 1
            elif error_category == "websocket":
                self.websocket_errors += 1
            elif error_category == "config":
                self.config_failures += 1
            elif error_category == "startup":
                self.startup_failures += 1

    def record_ws_connect(self) -> None:
        """Records a new WebSocket connection."""
        with self._lock:
            self.ws_active_connections += 1
            self.ws_total_connections += 1

    def record_ws_disconnect(self, duration_sec: float) -> None:
        """Records a WebSocket client disconnect and connection duration."""
        with self._lock:
            self.ws_active_connections = max(0, self.ws_active_connections - 1)
            self.ws_disconnects += 1
            self.ws_durations_sec.append(duration_sec)

    def record_ws_packet_sent(self, count: int = 1) -> None:
        """Records telemetry packets successfully transmitted over WebSocket."""
        now = time.monotonic()
        with self._lock:
            self.ws_telemetry_packets_sent += count
            for _ in range(count):
                self._ws_packet_timestamps.append(now)

    def record_ws_packet_dropped(self, count: int = 1) -> None:
        """Records telemetry packets dropped due to buffer overflow or backpressure."""
        with self._lock:
            self.ws_dropped_packets += count

    def record_ws_heartbeat_failure(self) -> None:
        """Records a WebSocket heartbeat timeout or failure."""
        with self._lock:
            self.ws_heartbeat_failures += 1

    def set_ws_configured_rate(self, rate_hz: float) -> None:
        """Updates the configured WebSocket stream rate."""
        with self._lock:
            self.ws_configured_stream_rate_hz = rate_hz

    def get_ws_observed_stream_rate(self) -> float:
        """Calculates observed telemetry packet rate (Hz) over recent sliding window."""
        with self._lock:
            if len(self._ws_packet_timestamps) < 2:
                return 0.0
            t_start = self._ws_packet_timestamps[0]
            t_end = self._ws_packet_timestamps[-1]
            dt = t_end - t_start
            if dt <= 0.001:
                return 0.0
            return round(float((len(self._ws_packet_timestamps) - 1) / dt), 2)

    def record_scenario_run(
        self,
        scenario_name: str,
        is_success: bool,
        duration_wall_sec: float,
        realtime_factor: float,
        final_position_error_m: float,
        decision_status: str,
    ) -> None:
        """Records quantitative execution metrics for a benchmark scenario."""
        with self._lock:
            if scenario_name not in self._scenarios:
                self._scenarios[scenario_name] = ScenarioMetricRecord(scenario_name)
            self._scenarios[scenario_name].record(
                is_success=is_success,
                duration_wall_sec=duration_wall_sec,
                realtime_factor=realtime_factor,
                final_position_error_m=final_position_error_m,
                decision_status=decision_status,
            )

    def get_http_metrics(self) -> Dict[str, Any]:
        """Returns aggregated HTTP request and latency metrics."""
        with self._lock:
            overall_latencies = list(self._overall_latencies_ms)
            route_stats = {
                route: LatencyStats.calculate(list(lat_deque))
                for route, lat_deque in self._route_latencies_ms.items()
            }

            return {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "slow_requests": self.slow_requests,
                "requests_by_method": dict(self.requests_by_method),
                "requests_by_endpoint": dict(self.requests_by_endpoint),
                "requests_by_status": dict(self.requests_by_status),
                "latency_overall": LatencyStats.calculate(overall_latencies),
                "latency_by_endpoint": route_stats,
            }

    def get_error_metrics(self) -> Dict[str, int]:
        """Returns error categorization counters."""
        with self._lock:
            return {
                "validation_errors": self.validation_errors,
                "scenario_execution_failures": self.scenario_execution_failures,
                "internal_errors": self.internal_errors,
                "websocket_errors": self.websocket_errors,
                "config_failures": self.config_failures,
                "startup_failures": self.startup_failures,
                "total_errors": (
                    self.validation_errors
                    + self.scenario_execution_failures
                    + self.internal_errors
                    + self.websocket_errors
                    + self.config_failures
                    + self.startup_failures
                ),
            }

    def get_websocket_metrics(self) -> Dict[str, Any]:
        """Returns WebSocket connection and streaming metrics."""
        with self._lock:
            durations = list(self.ws_durations_sec)
            return {
                "active_connections": self.ws_active_connections,
                "total_connections": self.ws_total_connections,
                "disconnects": self.ws_disconnects,
                "telemetry_packets_sent": self.ws_telemetry_packets_sent,
                "dropped_packets": self.ws_dropped_packets,
                "heartbeat_failures": self.ws_heartbeat_failures,
                "reconnect_events": self.ws_reconnect_events,
                "configured_stream_rate_hz": self.ws_configured_stream_rate_hz,
                "observed_stream_rate_hz": self.get_ws_observed_stream_rate(),
                "duration_stats": {
                    "avg_sec": round(float(np.mean(durations)), 2) if durations else 0.0,
                    "min_sec": round(float(np.min(durations)), 2) if durations else 0.0,
                    "max_sec": round(float(np.max(durations)), 2) if durations else 0.0,
                },
            }

    def get_scenario_metrics(self) -> Dict[str, Any]:
        """Returns scenario execution summaries."""
        with self._lock:
            total_execs = sum(s.executions for s in self._scenarios.values())
            total_success = sum(s.successful_executions for s in self._scenarios.values())
            total_failed = sum(s.failed_executions for s in self._scenarios.values())

            return {
                "total_executions": total_execs,
                "successful_executions": total_success,
                "failed_executions": total_failed,
                "scenarios": {k: v.to_dict() for k, v in self._scenarios.items()},
            }

    def reset(self) -> None:
        """Resets all metrics to initial state (used in testing)."""
        with self._lock:
            self.total_requests = 0
            self.requests_by_method.clear()
            self.requests_by_endpoint.clear()
            self.successful_requests = 0
            self.failed_requests = 0
            self.requests_by_status.clear()
            self.slow_requests = 0
            self._overall_latencies_ms.clear()
            self._route_latencies_ms.clear()
            self.validation_errors = 0
            self.scenario_execution_failures = 0
            self.internal_errors = 0
            self.websocket_errors = 0
            self.config_failures = 0
            self.startup_failures = 0
            self.ws_active_connections = 0
            self.ws_total_connections = 0
            self.ws_disconnects = 0
            self.ws_telemetry_packets_sent = 0
            self.ws_dropped_packets = 0
            self.ws_heartbeat_failures = 0
            self.ws_reconnect_events = 0
            self.ws_durations_sec.clear()
            self._ws_packet_timestamps.clear()
            self._scenarios.clear()


# Global singleton instance
metrics_collector = MetricsCollector()
