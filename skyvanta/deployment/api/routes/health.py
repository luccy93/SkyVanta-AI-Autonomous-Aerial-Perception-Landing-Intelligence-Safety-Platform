from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.contracts import DeploymentHealthContract, DeploymentReadinessContract
from skyvanta.deployment.health import HealthCheckService
from skyvanta.deployment.observability.health import readiness_service
from skyvanta.deployment.api.dependencies import get_deployment_config, get_health_service

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=DeploymentHealthContract,
    status_code=status.HTTP_200_OK,
    summary="Infrastructure Health & Safety Check",
    description="Evaluates operational health, uptime, simulation catalog status, and hardware isolation invariants.",
)
async def get_health(
    config: DeploymentConfig = Depends(get_deployment_config),
    health_service: HealthCheckService = Depends(get_health_service),
) -> DeploymentHealthContract:
    """Returns real-time deployment health status and verified safety isolation flags."""
    return health_service.check_health(deployment_config=config)


@router.get(
    "/ready",
    response_model=DeploymentReadinessContract,
    status_code=status.HTTP_200_OK,
    summary="Operational Traffic Readiness Probe",
    description="Verifies whether genuine operational dependencies (catalog, engine, safety locks) are ready to serve traffic.",
)
async def get_readiness(
    response: Response,
    config: DeploymentConfig = Depends(get_deployment_config),
) -> DeploymentReadinessContract:
    """Evaluates genuine operational dependencies to confirm traffic readiness."""
    readiness = readiness_service.check_readiness(deployment_config=config)
    if not readiness.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return readiness

