"""Batch execution harness and automated Markdown report generator for Volume 9 scenarios."""

from typing import Any, Dict, List, Optional
import numpy as np

from skyvanta.core.types import ScenarioMetrics
from skyvanta.simulation.engine import DigitalTwinEngine
from skyvanta.simulation.scenarios import ScenarioCatalog, ScenarioDefinition


class BatchScenarioRunner:
    """Runs automated batch validation across predefined scenarios and generates summary telemetry reports."""

    def __init__(self, engine: Optional[DigitalTwinEngine] = None):
        self.engine = engine or DigitalTwinEngine()

    def run_suite(
        self,
        scenarios: Optional[List[ScenarioDefinition]] = None,
        dt_sec: float = 0.05,
    ) -> Dict[str, Any]:
        """Executes all scenarios and returns a consolidated summary dictionary."""
        suite = scenarios or ScenarioCatalog.get_full_suite()
        results: List[ScenarioMetrics] = []

        for scenario in suite:
            metrics, _ = self.engine.run_scenario(scenario, dt_sec=dt_sec)
            results.append(metrics)

        total_scenarios = len(results)
        passed_count = sum(1 for m in results if m.success)
        pass_rate = float(passed_count / max(1, total_scenarios)) * 100.0

        mean_rmse = float(np.mean([m.rmse_position_m for m in results]))
        max_err = float(np.max([m.max_estimation_error_m for m in results]))
        mean_consistency = float(np.mean([m.nees_consistency_fraction for m in results])) * 100.0

        summary = {
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_count,
            "pass_rate_percent": pass_rate,
            "mean_rmse_position_m": mean_rmse,
            "max_estimation_error_m": max_err,
            "mean_consistency_percent": mean_consistency,
            "scenarios": [m.model_dump() for m in results],
        }

        return summary

    @staticmethod
    def generate_markdown_report(summary: Dict[str, Any]) -> str:
        """Renders summary results into a GitHub-flavored Markdown report."""
        md = []
        md.append("# SkyVanta AI — Digital Twin Scenario Validation Report\n")
        md.append(f"**Overall Pass Rate**: {summary['pass_rate_percent']:.1f}% ({summary['passed_scenarios']}/{summary['total_scenarios']} Scenarios Passed)\n")
        md.append(f"**Mean Position RMSE**: {summary['mean_rmse_position_m']:.3f} m\n")
        md.append(f"**Max Estimation Error**: {summary['max_estimation_error_m']:.3f} m\n")
        md.append(f"**Estimator Consistency ($3\\sigma$)**: {summary['mean_consistency_percent']:.1f}%\n\n")

        md.append("## Scenario Execution Breakdown\n\n")
        md.append("| Scenario Name | Outcome | Duration (s) | Final Pos Err (m) | Final $v_z$ (m/s) | Result |\n")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- |\n")

        for sc in summary["scenarios"]:
            res_str = "✅ PASS" if sc["success"] else "❌ FAIL"
            md.append(
                f"| `{sc['scenario_name']}` | `{sc['outcome']}` | {sc['duration_sec']:.2f}s | "
                f"{sc['final_position_error_m']:.3f}m | {sc['final_velocity_mps']:.2f}m/s | {res_str} |\n"
            )

        return "".join(md)
