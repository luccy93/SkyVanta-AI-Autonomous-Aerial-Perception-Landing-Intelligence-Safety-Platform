"""FastAPI dependency injection providers for configuration, health, simulation, and telemetry services."""

from fastapi import Request, WebSocket

from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.health import HealthCheckService
from skyvanta.deployment.api.services.simulation_service import SimulationService
from skyvanta.deployment.api.services.telemetry_service import TelemetryService


def get_deployment_config(request: Request) -> DeploymentConfig:
    """Returns DeploymentConfig attached to application state or from environment."""
    if hasattr(request.app.state, "config") and request.app.state.config is not None:
        return request.app.state.config
    return DeploymentConfig.from_env()


def get_deployment_config_ws(websocket: WebSocket) -> DeploymentConfig:
    """Returns DeploymentConfig attached to application state for WebSocket endpoints."""
    if hasattr(websocket.app.state, "config") and websocket.app.state.config is not None:
        return websocket.app.state.config
    return DeploymentConfig.from_env()


def get_health_service(request: Request) -> HealthCheckService:
    """Returns HealthCheckService attached to application state or new instance."""
    if hasattr(request.app.state, "health_service") and request.app.state.health_service is not None:
        return request.app.state.health_service
    return HealthCheckService()


def get_simulation_service() -> SimulationService:
    """Returns a new instance of SimulationService."""
    return SimulationService()


def get_telemetry_service_ws(websocket: WebSocket) -> TelemetryService:
    """Returns TelemetryService attached to application state for WebSocket endpoints."""
    if hasattr(websocket.app.state, "telemetry_service") and websocket.app.state.telemetry_service is not None:
        return websocket.app.state.telemetry_service
    return TelemetryService()


def get_request_id(request: Request) -> str:
    """Extracts correlated request ID from request state."""
    return getattr(request.state, "request_id", "req_unknown")
