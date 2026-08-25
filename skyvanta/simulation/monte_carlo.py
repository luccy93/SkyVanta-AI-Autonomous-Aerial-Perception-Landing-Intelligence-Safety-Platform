"""Monte Carlo statistical experiment framework for Digital Twin robustness evaluation."""

from typing import List, Optional, Tuple
import numpy as np

from skyvanta.core.types import (
    ExperimentResult,
    ExperimentStatistics,
    ScenarioOutcome,
)
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.scenarios import Scenario


class MonteCarloRunner:
    """Executes stochastic batches of scenario simulations with distinct random seeds."""

    def __init__(self, engine: Optional[ScenarioEngine] = None):
        self.engine = engine or ScenarioEngine()

    def run_batch(
        self,
        scenario: Scenario,
        number_of_runs: int = 20,
        base_seed: int = 1000,
    ) -> Tuple[ExperimentStatistics, List[ExperimentResult]]:
        """Executes N runs where seed_i = base_seed + i and compiles statistical distribution.

        Args:
            scenario: Base Scenario definition template.
            number_of_runs: Total number of iterations (N >= 1).
            base_seed: Starting integer seed.

        Returns:
            (ExperimentStatistics, list_of_ExperimentResults)
        """
        if number_of_runs < 1:
            raise ValueError(f"number_of_runs must be at least 1 (got {number_of_runs})")

        results: List[ExperimentResult] = []
        pos_rmses: List[float] = []
        peak_pos_errors: List[float] = []
        vel_errors: List[float] = []
        peak_uncertainties: List[float] = []
        landing_times: List[float] = []

        success_count = 0
        abort_count = 0
        fault_count = 0
        recovery_count = 0
        total_violations = 0

        for i in range(number_of_runs):
            seed_i = base_seed + i
            run_id = f"mc_run_{i+1:04d}_seed_{seed_i}"

            # Create run scenario with specific seed
            scen_dict = scenario.model_dump()
            scen_dict["seed"] = seed_i
            run_scenario = Scenario(**scen_dict)

            res, _ = self.engine.run(run_scenario, run_id=run_id)
            results.append(res)

            if res.metrics.success:
                success_count += 1
            if res.status == ScenarioOutcome.SUCCESS_ABORTED:
                abort_count += 1
            elif res.status in (ScenarioOutcome.FAILED_CRASH, ScenarioOutcome.FAILED_SAFETY_VIOLATION):
                fault_count += 1
            elif res.status == ScenarioOutcome.SUCCESS_RECOVERED:
                recovery_count += 1

            total_violations += len(res.safety_violations)

            pos_rmses.append(res.metrics.rmse_position_m)
            peak_pos_errors.append(res.metrics.max_estimation_error_m)
            vel_errors.append(res.metrics.final_velocity_mps)
            if res.landing_confirmed:
                landing_times.append(res.duration_sec)

        n = float(number_of_runs)
        mean_rmse = float(np.mean(pos_rmses)) if pos_rmses else 0.0
        median_rmse = float(np.median(pos_rmses)) if pos_rmses else 0.0
        p95_pos = float(np.percentile(peak_pos_errors, 95)) if peak_pos_errors else 0.0
        p99_pos = float(np.percentile(peak_pos_errors, 99)) if peak_pos_errors else 0.0
        mean_vel = float(np.mean(vel_errors)) if vel_errors else 0.0
        p95_vel = float(np.percentile(vel_errors, 95)) if vel_errors else 0.0

        mean_landing_t = float(np.mean(landing_times)) if landing_times else 0.0
        p95_landing_t = float(np.percentile(landing_times, 95)) if landing_times else 0.0

        stats = ExperimentStatistics(
            total_runs=number_of_runs,
            success_rate=float(success_count / n),
            abort_rate=float(abort_count / n),
            fault_rate=float(fault_count / n),
            recovery_rate=float(recovery_count / n),
            mean_position_rmse=mean_rmse,
            median_position_rmse=median_rmse,
            p95_position_error=p95_pos,
            p99_position_error=p99_pos,
            mean_velocity_error=mean_vel,
            p95_velocity_error=p95_vel,
            max_uncertainty_m=float(np.max(peak_pos_errors)) if peak_pos_errors else 0.0,
            mean_landing_time_sec=mean_landing_t,
            p95_landing_time_sec=p95_landing_t,
            total_safety_violations=total_violations,
        )

        return stats, results
