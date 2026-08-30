"""System metadata and capability discovery routes."""

from typing import List
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.api.dependencies import get_deployment_config

try:
    import importlib.metadata as importlib_metadata
    __version__ = importlib_metadata.version("skyvanta")
except Exception:
    __version__ = "0.1.0"

router = APIRouter(prefix="/api/v1/system", tags=["System"])


class SystemInfoResponse(BaseModel):
    """System information and platform capability disclosure model."""

    application: str = Field(
        default="SkyVanta AI",
        description="Application brand and platform name.",
    )
    version: str = Field(
        description="SkyVanta AI core package release version.",
    )
    api_version: str = Field(
        default="v1",
        description="Active REST API specification version.",
    )
    environment: str = Field(
        description="Active deployment tier (development, testing, production).",
    )
    git_commit: str = Field(
        default="unknown",
        description="Safe Git commit identifier.",
    )
    build_timestamp: str = Field(
        default="2026-08-30T00:00:00Z",
        description="Build or packaging timestamp.",
    )
    hardware_access: bool = Field(
        default=False,
        description="Hardware connectivity status (strictly False).",
    )
    network_model_download: bool = Field(
        default=False,
        description="Network model download status (strictly False).",
    )
    safety_boundary_enforced: bool = Field(
        default=True,
        description="Software safety invariant enforcement status.",
    )
    supported_capabilities: List[str] = Field(
        description="List of verified algorithmic and simulation capabilities.",
    )


@router.get(
    "/info",
    response_model=SystemInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="System Information & Platform Capabilities",
    description="Returns public non-sensitive platform metadata, versioning, and verified capabilities.",
)
async def get_system_info(
    config: DeploymentConfig = Depends(get_deployment_config),
) -> SystemInfoResponse:
    """Returns application name, version, environment, and capability manifest."""
    from skyvanta.deployment.observability.runtime import system_resource_monitor
    git_commit = config.git_commit or system_resource_monitor.get_git_commit()
    build_ts = config.build_timestamp or system_resource_monitor.get_build_timestamp()

    return SystemInfoResponse(
        application="SkyVanta AI",
        version=__version__,
        api_version="v1",
        environment=config.environment.value,
        git_commit=git_commit,
        build_timestamp=build_ts,
        hardware_access=False,
        network_model_download=False,
        safety_boundary_enforced=True,
        supported_capabilities=[
            "6_dof_digital_twin_simulation",
            "15_state_esekf_sensor_fusion",
            "monocular_6dof_pnp_localization",
            "multi_target_kf_tracking",
            "12_state_safety_fsm_supervision",
            "rate_limited_flight_command_authorization",
            "deterministic_scenario_replay",
            "monte_carlo_batch_validation",
        ],
    )
