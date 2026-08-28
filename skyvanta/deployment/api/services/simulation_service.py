"""Simulation service adapter orchestrating digital twin executions for API requests."""

import time
from typing import Optional
from starlette.concurrency import run_in_threadpool

from skyvanta.core.exceptions import SkyVantaError
from skyvanta.deployment.contracts import ScenarioRunRequest, ScenarioRunResponse
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.registry import ScenarioRegistry


class ScenarioNotFoundError(SkyVantaError):
    """Raised when a requested scenario is not found in the ScenarioRegistry."""
    pass


class SimulationService:
    """Provides a thin service boundary over the closed-loop ScenarioEngine."""

    async def execute_scenario(
        self,
        request: ScenarioRunRequest,
        request_id: Optional[str] = None,
    ) -> ScenarioRunResponse:
        """Executes a simulation scenario asynchronously in a background threadpool.

        Args:
            request: ScenarioRunRequest parameters.
            request_id: Optional correlation request ID.

        Returns:
            ScenarioRunResponse with quantitative simulation metrics.
        """
        return await run_in_threadpool(self._sync_execute_scenario, request, request_id)

    def _sync_execute_scenario(
        self,
        request: ScenarioRunRequest,
        request_id: Optional[str] = None,
    ) -> ScenarioRunResponse:
        """Synchronous implementation of scenario execution."""
        scenario = ScenarioRegistry.get(request.scenario_name)
        if scenario is None:
            raise ScenarioNotFoundError(
                f"Benchmark scenario '{request.scenario_name}' not found in registry."
            )

        # Apply runtime request parameter overrides
        updates = {}
        if request.seed is not None:
            updates["seed"] = request.seed
        if request.max_duration_sec is not None and request.max_duration_sec > 0:
            updates["duration_sec"] = request.max_duration_sec

        if updates:
            scenario = scenario.model_copy(update=updates)

        run_id = f"api_run_{request.scenario_name}_{request.seed}_{request_id or int(time.time())}"

        t_wall_start = time.perf_counter()
        engine = ScenarioEngine()
        exp_result, _ = engine.run(scenario, run_id=run_id)
        duration_wall = time.perf_counter() - t_wall_start

        realtime_factor = (
            float(exp_result.duration_sec) / max(duration_wall, 1e-5)
            if duration_wall > 0
            else 0.0
        )

        is_success = (
            exp_result.status.value.lower() == "success_landed"
            and len(exp_result.safety_violations) == 0
        )

        return ScenarioRunResponse(
            run_id=exp_result.run_id,
            scenario_name=exp_result.scenario_id,
            status=exp_result.status.value,
            seed=exp_result.seed,
            duration_sim_sec=round(float(exp_result.duration_sec), 3),
            duration_wall_sec=round(float(duration_wall), 4),
            realtime_factor=round(float(realtime_factor), 2),
            final_position_error_m=round(float(exp_result.metrics.final_position_error_m), 4),
            rmse_position_m=round(float(exp_result.metrics.rmse_position_m), 4),
            safety_violations_count=len(exp_result.safety_violations),
            is_success=is_success,
            error_message=None,
        )
