"""FastAPI application factory and centralized exception handling."""

from contextlib import asynccontextmanager
import logging
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from skyvanta.core.exceptions import SkyVantaError
from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.health import HealthCheckService
from skyvanta.deployment.logging import DeploymentLogger
from skyvanta.deployment.api.middleware import RequestIDMiddleware
from skyvanta.deployment.api.routes import (
    health_router,
    scenarios_router,
    simulation_router,
    system_router,
    telemetry_router,
)
from skyvanta.deployment.api.services.simulation_service import ScenarioNotFoundError
from skyvanta.deployment.api.services.telemetry_service import TelemetryService

try:
    import importlib.metadata as importlib_metadata
    __version__ = importlib_metadata.version("skyvanta")
except Exception:
    __version__ = "0.1.0"

logger = logging.getLogger("skyvanta.api")


def create_app(config: Optional[DeploymentConfig] = None) -> FastAPI:
    """Creates and configures the production FastAPI application instance."""
    app_config = config or DeploymentConfig.from_env()

    # Configure structured logger
    DeploymentLogger.configure_logging(
        level=app_config.log_level,
        json_format=(app_config.environment.value == "production"),
        logger_name="skyvanta.api",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(
            "SkyVanta AI API server starting in %s mode (Host: %s, Port: %d)",
            app_config.environment.value,
            app_config.host,
            app_config.port,
        )
        yield
        logger.info("SkyVanta AI API server shutting down.")
        if hasattr(app.state, "telemetry_service") and app.state.telemetry_service is not None:
            await app.state.telemetry_service.shutdown()

    tags_metadata = [
        {
            "name": "Health",
            "description": "Infrastructure liveness, readiness, and safety boundary verification.",
        },
        {
            "name": "System",
            "description": "Platform versioning, metadata, and capability discovery.",
        },
        {
            "name": "Scenarios",
            "description": "Digital twin benchmark landing scenario catalog and definitions.",
        },
        {
            "name": "Simulation",
            "description": "Closed-loop 6-DoF digital twin simulation execution and compliance scoring.",
        },
        {
            "name": "Telemetry",
            "description": "Real-time closed-loop digital twin telemetry WebSocket streaming.",
        },
    ]

    app = FastAPI(
        title="SkyVanta AI",
        version=__version__,
        description=(
            "SkyVanta AI — Autonomous Aerial Perception, 15-State Sensor Fusion, "
            "Safety Supervision & Digital Twin Simulation Service Layer."
        ),
        openapi_tags=tags_metadata,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Attach state for dependency injection
    app.state.config = app_config
    app.state.health_service = HealthCheckService()
    app.state.telemetry_service = TelemetryService()

    # 1. CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 2. Request Correlation ID Middleware
    app.add_middleware(RequestIDMiddleware)

    # 3. Exception Handlers
    @app.exception_handler(ScenarioNotFoundError)
    async def scenario_not_found_handler(request: Request, exc: ScenarioNotFoundError):
        req_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": "scenario_not_found",
                "message": str(exc),
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(SkyVantaError)
    async def skyvanta_domain_error_handler(request: Request, exc: SkyVantaError):
        req_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "skyvanta_domain_error",
                "message": str(exc),
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        req_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "message": exc.detail,
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Invalid request payload",
                "details": exc.errors(),
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        req_id = getattr(request.state, "request_id", "unknown")
        logger.error("Unhandled exception for request %s: %s", req_id, str(exc), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected internal server error occurred.",
                "request_id": req_id,
            },
            headers={"X-Request-ID": req_id},
        )

    # 4. Include Routers
    app.include_router(health_router)
    app.include_router(system_router)
    app.include_router(scenarios_router)
    app.include_router(simulation_router)
    app.include_router(telemetry_router)

    return app


# Default application instance for ASGI servers (uvicorn skyvanta.deployment.api.app:app)
app = create_app()
