"""Deployment infrastructure health check route."""

from fastapi import APIRouter, Depends, status

from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.contracts import DeploymentHealthContract
from skyvanta.deployment.health import HealthCheckService
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
