"""Performance benchmarking for Digital Twin simulation and pipeline throughput."""

import time
from typing import Any, Dict, List, Optional
import numpy as np

from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.registry import ScenarioRegistry
from skyvanta.simulation.scenarios import Scenario


class SimulationBenchmark:
    """Measures execution latency, throughput, and real-time factor for simulations."""

    def __init__(self, engine: Optional[ScenarioEngine] = None):
        self.engine = engine or ScenarioEngine()

    def benchmark_scenario(
        self,
        scenario: Scenario,
        iterations: int = 3,
    ) -> Dict[str, Any]:
        """Runs scenario multiple times and benchmarks execution timing."""
        wall_times: List[float] = []
        sim_times: List[float] = []
        step_counts: List[int] = []

        for i in range(iterations):
            t_start = time.perf_counter()
            result, traj = self.engine.run(scenario, run_id=f"bench_{i}")
            t_wall = time.perf_counter() - t_start

            wall_times.append(t_wall)
            sim_times.append(result.duration_sec)
            step_counts.append(len(traj))

        mean_wall_sec = float(np.mean(wall_times))
        mean_sim_sec = float(np.mean(sim_times))
        total_steps = sum(step_counts)
        mean_steps_per_run = float(np.mean(step_counts))
        mean_step_latency_ms = (mean_wall_sec / max(1, mean_steps_per_run)) * 1000.0
        realtime_factor = mean_sim_sec / max(1e-6, mean_wall_sec)

        return {
            "scenario_name": scenario.name,
            "iterations": iterations,
            "mean_sim_time_sec": mean_sim_sec,
            "mean_wall_time_sec": mean_wall_sec,
            "realtime_factor_x": realtime_factor,
            "mean_step_latency_ms": mean_step_latency_ms,
            "total_steps_executed": total_steps,
            "throughput_steps_per_sec": total_steps / max(1e-6, sum(wall_times)),
        }
