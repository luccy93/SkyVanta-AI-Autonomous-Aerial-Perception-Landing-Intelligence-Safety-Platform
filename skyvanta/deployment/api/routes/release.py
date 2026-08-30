"""Production release metadata and verification status route."""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from skyvanta.deployment.config import DeploymentConfig
from skyvanta.deployment.api.dependencies import get_deployment_config
from skyvanta.deployment.release.manifest import ReleaseManifest
from skyvanta.deployment.release.verifier import ReleaseVerifier
from skyvanta.deployment.security import require_scope, Scope, APIKeyRecord

try:
    import importlib.metadata as importlib_metadata
    __version__ = importlib_metadata.version("skyvanta")
except Exception:
    __version__ = "0.1.0"

router = APIRouter(prefix="/api/v1/release", tags=["Release"])


class ReleaseResponse(BaseModel):
    """Production release metadata and pre-flight verification contract."""

    application: str = Field(
        default="SkyVanta AI",
        description="Application platform brand.",
    )
    version: str = Field(
        description="Software release version string.",
    )
    api_version: str = Field(
        default="v1",
        description="Active REST & WebSocket API specification version.",
    )
    git_commit: str = Field(
        description="Safe Git commit identifier.",
    )
    environment: str = Field(
        description="Active deployment tier (development, testing, production).",
    )
    core_version: str = Field(
        default="V1-V9",
        description="Frozen robotics core architecture milestone.",
    )
    hardware_access: bool = Field(
        default=False,
        description="Hardware connectivity status (strictly False).",
    )
    network_model_download: bool = Field(
        default=False,
        description="Network model download status (strictly False).",
    )
    release_verified: bool = Field(
        description="Whether release verification checks passed successfully.",
    )


@router.get(
    "",
    response_model=ReleaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Release Metadata & Verification Status",
    description="Returns public non-sensitive release metadata and verifies that safety boundaries are intact.",
)
async def get_release_info(
    config: DeploymentConfig = Depends(get_deployment_config),
    _auth: APIKeyRecord = Depends(require_scope(Scope.READ)),
) -> ReleaseResponse:
    """Returns release metadata, git commit hash, and verification status."""
    verifier = ReleaseVerifier()
    manifest = ReleaseManifest.generate(
        environment=config.environment.value,
        test_count=399,
    )
    # If config specifies git commit override, apply it
    if config.git_commit:
        manifest.git_commit = config.git_commit

    verification_result = verifier.verify(
        deployment_config=config,
        manifest=manifest,
    )

    return ReleaseResponse(
        application=manifest.application_name,
        version=manifest.version,
        api_version=manifest.api_version,
        git_commit=manifest.git_commit,
        environment=config.environment.value,
        core_version=manifest.core_architecture_version,
        hardware_access=manifest.hardware_access,
        network_model_download=manifest.network_model_download,
        release_verified=verification_result.passed,
    )
