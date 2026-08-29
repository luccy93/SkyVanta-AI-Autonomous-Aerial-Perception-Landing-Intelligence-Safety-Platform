"""API routes module exports."""

from skyvanta.deployment.api.routes.health import router as health_router
from skyvanta.deployment.api.routes.scenarios import router as scenarios_router
from skyvanta.deployment.api.routes.simulation import router as simulation_router
from skyvanta.deployment.api.routes.system import router as system_router
from skyvanta.deployment.api.routes.telemetry import router as telemetry_router

__all__ = [
    "health_router",
    "system_router",
    "scenarios_router",
    "simulation_router",
    "telemetry_router",
]
