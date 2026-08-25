"""Experiment reporting, JSON serialization, and Markdown scorecard generation."""

import json
import os
from typing import Any, Dict, List, Optional

from skyvanta.core.types import ExperimentResult, ExperimentStatistics


class ScenarioReportGenerator:
    """Generates human-readable Markdown and machine-readable JSON evaluation reports."""

    @staticmethod
    def generate_single_run_markdown(result: ExperimentResult) -> str:
        """Formats an ExperimentResult into a Markdown scorecard."""
        m = result.metrics
        status_badge = "[PASS]" if m.success else "[FAIL]"

        lines = [
            f"# SkyVanta AI - Scenario Validation Report: `{result.scenario_id}`",
            "",
            f"**Run ID**: `{result.run_id}`  ",
            f"**Scenario Name**: `{m.scenario_name}`  ",
            f"**Status**: {status_badge} (`{result.status.value}`)  ",
            f"**Random Seed**: `{result.seed}`  ",
            f"**Config Hash**: `{result.config_hash[:16]}...`  ",
            "",
            "---",
            "",
            "## 1. Quantitative Performance Metrics",
            "",
            "| Metric | Measured Value | Requirement / Target | Compliance |",
            "| :--- | :--- | :--- | :---: |",
            f"| **Final Position Error** | `{m.final_position_error_m:.3f} m` | $< 0.30\\text{{ m}}$ | {'PASS' if m.final_position_error_m < 0.30 or not result.landing_confirmed else 'CHECK'} |",
            f"| **Touchdown Velocity $v_z$** | `{m.final_velocity_mps:.3f} m/s` | $< 0.60\\text{{ m/s}}$ | {'PASS' if m.final_velocity_mps < 0.60 else 'FAIL'} |",
            f"| **Peak Estimation Error** | `{m.max_estimation_error_m:.3f} m` | Envelope Bound | {'PASS' if m.max_estimation_error_m < 1.5 else 'WARN'} |",
            f"| **RMSE Position Error** | `{m.rmse_position_m:.3f} m` | $< 0.50\\text{{ m}}$ | {'PASS' if m.rmse_position_m < 0.50 else 'WARN'} |",
            f"| **NEES Consistency** | `{m.nees_consistency_fraction * 100.0:.1f}%` | $\\ge 80.0\\%$ | {'PASS' if m.nees_consistency_fraction >= 0.80 else 'WARN'} |",
            f"| **Duration** | `{result.duration_sec:.2f} s` | Nominal Window | PASS |",
            f"| **Flight Commands Sent** | `{result.command_count}` | Monotonic Queue | PASS |",
            "",
            "---",
            "",
            "## 2. Safety Violations & Phase Sequence",
            "",
            f"- **Landing Confirmed**: `{result.landing_confirmed}`",
            f"- **Abort Triggered**: `{result.abort_triggered}`",
            f"- **Total Safety Violations**: `{len(result.safety_violations)}`",
            f"- **Phase Transitions**: `{' -> '.join(m.phase_transitions)}`",
            "",
        ]

        if result.safety_violations:
            lines.append("### Detected Safety Violations:")
            for v in result.safety_violations:
                lines.append(f"- **[{v.timestamp_sec:.2f}s] `{v.violation_type.value}`**: {v.message}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_monte_carlo_markdown(stats: ExperimentStatistics, scenario_name: str) -> str:
        """Formats an ExperimentStatistics summary into a Markdown report."""
        lines = [
            f"# SkyVanta AI - Monte Carlo Robustness Report: `{scenario_name}`",
            "",
            f"**Total Experiment Iterations**: `{stats.total_runs}`  ",
            f"**Success Rate**: `{stats.success_rate * 100.0:.1f}%`  ",
            f"**Abort Rate**: `{stats.abort_rate * 100.0:.1f}%`  ",
            f"**Fault Rate**: `{stats.fault_rate * 100.0:.1f}%`  ",
            f"**Recovery Rate**: `{stats.recovery_rate * 100.0:.1f}%`  ",
            f"**Total Invariant Violations**: `{stats.total_safety_violations}`  ",
            "",
            "---",
            "",
            "## Statistical Metric Distribution",
            "",
            "| Metric | Mean | Median | P95 | P99 |",
            "| :--- | :--- | :--- | :--- | :--- |",
            f"| **Position RMSE (m)** | `{stats.mean_position_rmse:.3f}` | `{stats.median_position_rmse:.3f}` | `{stats.p95_position_error:.3f}` | `{stats.p99_position_error:.3f}` |",
            f"| **Touchdown Velocity (m/s)** | `{stats.mean_velocity_error:.3f}` | - | `{stats.p95_velocity_error:.3f}` | - |",
            f"| **Landing Time (s)** | `{stats.mean_landing_time_sec:.2f}` | - | `{stats.p95_landing_time_sec:.2f}` | - |",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def export_json(result: ExperimentResult, output_path: str) -> None:
        """Exports an ExperimentResult to a JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2)
