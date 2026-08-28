"""Digital Twin benchmark scenario catalog discovery routes."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from skyvanta.simulation.registry import ScenarioRegistry

router = APIRouter(prefix="/api/v1/scenarios", tags=["Scenarios"])


class ScenarioCatalogItem(BaseModel):
    """Summarized digital twin benchmark scenario catalog item."""

    scenario_id: str = Field(
        description="Unique formal identifier (e.g. SCN_NOMINAL_01).",
    )
    name: str = Field(
        description="Canonical scenario name (e.g. nominal_landing).",
    )
    description: str = Field(
        description="Detailed scenario description and environmental focus.",
    )
    duration_sec: float = Field(
        description="Nominal simulation timeout in seconds.",
    )
    timestep_sec: float = Field(
        description="Integration timestep in seconds.",
    )
    seed: int = Field(
        description="Default pseudo-random generator seed.",
    )
    expected_outcome: str = Field(
        description="Expected pass outcome classification (e.g. SUCCESS_LANDED, ABORTED).",
    )
    events_count: int = Field(
        description="Number of dynamic perturbation events configured.",
    )


class ScenarioDetailItem(ScenarioCatalogItem):
    """Detailed digital twin benchmark scenario definition."""

    initial_vehicle_pos: List[float] = Field(
        description="Starting vehicle position [x, y, z] in meters.",
    )
    initial_vehicle_vel: List[float] = Field(
        description="Starting vehicle velocity [vx, vy, vz] in m/s.",
    )
    initial_vehicle_euler_deg: List[float] = Field(
        description="Starting vehicle attitude [roll, pitch, yaw] in degrees.",
    )
    events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Configured dynamic disturbance and sensor fault events.",
    )


@router.get(
    "",
    response_model=List[ScenarioCatalogItem],
    status_code=status.HTTP_200_OK,
    summary="List Scenario Catalog",
    description="Returns the full catalog of registered 6-DoF digital twin benchmark landing scenarios.",
)
async def list_scenarios() -> List[ScenarioCatalogItem]:
    """Lists all available standard benchmark landing scenarios."""
    scenarios = ScenarioRegistry.get_all_scenarios()
    catalog = []
    for s in scenarios:
        catalog.append(
            ScenarioCatalogItem(
                scenario_id=s.scenario_id,
                name=s.name,
                description=s.description,
                duration_sec=s.duration_sec,
                timestep_sec=s.timestep_sec,
                seed=s.seed,
                expected_outcome=s.expected_outcome.value,
                events_count=len(s.events),
            )
        )
    return catalog


@router.get(
    "/{scenario_name}",
    response_model=ScenarioDetailItem,
    status_code=status.HTTP_200_OK,
    summary="Get Scenario Details",
    description="Retrieves detailed kinematic and environmental configuration for a named benchmark scenario.",
)
async def get_scenario_details(scenario_name: str) -> ScenarioDetailItem:
    """Retrieves full specification for a specific benchmark scenario."""
    scenario = ScenarioRegistry.get(scenario_name)
    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark scenario '{scenario_name}' not found in registry.",
        )

    events_summary = []
    for ev in scenario.events:
        events_summary.append({
            "event_type": ev.event_type.value,
            "timestamp_sec": ev.timestamp_sec,
            "duration_sec": ev.duration_sec,
            "parameters": ev.parameters,
        })

    return ScenarioDetailItem(
        scenario_id=scenario.scenario_id,
        name=scenario.name,
        description=scenario.description,
        duration_sec=scenario.duration_sec,
        timestep_sec=scenario.timestep_sec,
        seed=scenario.seed,
        expected_outcome=scenario.expected_outcome.value,
        events_count=len(scenario.events),
        initial_vehicle_pos=list(scenario.initial_vehicle_pos),
        initial_vehicle_vel=list(scenario.initial_vehicle_vel),
        initial_vehicle_euler_deg=list(scenario.initial_vehicle_euler_deg),
        events=events_summary,
    )
