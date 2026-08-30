"""Operational metrics and diagnostic discovery route."""

import time
from fastapi import APIRouter, Depends, status

from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.contracts import MetricsResponseContract
from skyvanta.deployment.observability.events import event_logger
from skyvanta.deployment.observability.metrics import metrics_collector
from skyvanta.deployment.observability.runtime import system_resource_monitor
from skyvanta.deployment.api.dependencies import get_deployment_config
from skyvanta.deployment.security import require_scope, Scope, APIKeyRecord

try:
    import importlib.metadata as importlib_metadata
    __version__ = importlib_metadata.version("skyvanta")
except Exception:
    __version__ = "0.1.0"

router = APIRouter(prefix="/api/v1/metrics", tags=["Observability"])


@router.get(
    "",
    response_model=MetricsResponseContract,
    status_code=status.HTTP_200_OK,
    summary="Operational Metrics & Telemetry",
    description=(
        "Returns machine-readable application-level operational metrics including "
        "HTTP request volume, exact latency percentiles (min, avg, p50, p95, p99, max), "
        "WebSocket connection stats, benchmark scenario executions, and system resource utilization."
    ),
)
async def get_metrics(
    config: DeploymentConfig = Depends(get_deployment_config),
    _auth: APIKeyRecord = Depends(require_scope(Scope.READ)),
) -> MetricsResponseContract:
    """Collects and returns active operational telemetry and performance metrics."""
    http_metrics = metrics_collector.get_http_metrics()
    error_metrics = metrics_collector.get_error_metrics()
    ws_metrics = metrics_collector.get_websocket_metrics()
    scenario_metrics = metrics_collector.get_scenario_metrics()
    sys_metrics = system_resource_monitor.get_resource_usage()

    warnings = system_resource_monitor.evaluate_warnings(
        cpu_threshold_pct=config.cpu_warning_threshold_pct,
        memory_threshold_mb=config.memory_warning_threshold_mb,
        max_ws_clients=config.max_ws_clients,
        active_ws_clients=ws_metrics["active_connections"],
    )

    recent_events = event_logger.get_recent_events(limit=20)

    return MetricsResponseContract(
        service="skyvanta-api",
        version=__version__,
        environment=config.environment.value,
        timestamp_sec=round(time.time(), 3),
        http=http_metrics,
        errors=error_metrics,
        websockets=ws_metrics,
        scenarios=scenario_metrics,
        system=sys_metrics,
        warnings=warnings,
        recent_events=recent_events,
    )
