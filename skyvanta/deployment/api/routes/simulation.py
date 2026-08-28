"""Closed-loop Digital Twin simulation execution routes."""

from fastapi import APIRouter, Depends, status

from skyvanta.deployment.contracts import ScenarioRunRequest, ScenarioRunResponse
from skyvanta.deployment.api.dependencies import get_request_id, get_simulation_service
from skyvanta.deployment.api.services.simulation_service import SimulationService

router = APIRouter(prefix="/api/v1/scenarios", tags=["Simulation"])


@router.post(
    "/run",
    response_model=ScenarioRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Simulation Scenario",
    description="Executes a 6-DoF closed-loop digital twin landing simulation and returns quantitative compliance metrics.",
)
async def run_scenario(
    request: ScenarioRunRequest,
    simulation_service: SimulationService = Depends(get_simulation_service),
    request_id: str = Depends(get_request_id),
) -> ScenarioRunResponse:
    """Executes a benchmark scenario through the verified simulation engine."""
    return await simulation_service.execute_scenario(request, request_id=request_id)
