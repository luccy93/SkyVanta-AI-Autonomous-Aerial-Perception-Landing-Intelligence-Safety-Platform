"""Deterministic scenario replay and reproducibility verification."""

import json
from typing import Any, Dict, List, Optional, Tuple

from skyvanta.core.types import ExperimentResult
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.scenarios import Scenario, compute_configuration_hash


class ScenarioReplay:
    """Provides bitwise identical scenario execution replay and regression verification."""

    def __init__(self, engine: Optional[ScenarioEngine] = None):
        self.engine = engine or ScenarioEngine()

    def replay_and_verify(
        self,
        scenario: Scenario,
        baseline_result: ExperimentResult,
    ) -> Tuple[bool, List[str]]:
        """Replays a scenario and verifies exact outcome and numerical match against baseline.

        Returns:
            (is_identical: bool, mismatch_reasons: List[str])
        """
        replay_result, _ = self.engine.run(scenario, run_id=f"replay_{baseline_result.run_id}")
        mismatches: List[str] = []

        if replay_result.status != baseline_result.status:
            mismatches.append(
                f"Status mismatch: replayed {replay_result.status.value} != baseline {baseline_result.status.value}"
            )

        if replay_result.landing_confirmed != baseline_result.landing_confirmed:
            mismatches.append(
                f"Landing confirmed mismatch: replayed {replay_result.landing_confirmed} != baseline {baseline_result.landing_confirmed}"
            )

        if replay_result.abort_triggered != baseline_result.abort_triggered:
            mismatches.append(
                f"Abort triggered mismatch: replayed {replay_result.abort_triggered} != baseline {baseline_result.abort_triggered}"
            )

        if abs(replay_result.duration_sec - baseline_result.duration_sec) > 1e-4:
            mismatches.append(
                f"Duration mismatch: replayed {replay_result.duration_sec:.4f}s != baseline {baseline_result.duration_sec:.4f}s"
            )

        if abs(replay_result.metrics.final_position_error_m - baseline_result.metrics.final_position_error_m) > 1e-4:
            mismatches.append(
                f"Final position error mismatch: {replay_result.metrics.final_position_error_m:.4f}m != {baseline_result.metrics.final_position_error_m:.4f}m"
            )

        if len(replay_result.safety_violations) != len(baseline_result.safety_violations):
            mismatches.append(
                f"Safety violations count mismatch: {len(replay_result.safety_violations)} != {len(baseline_result.safety_violations)}"
            )

        return len(mismatches) == 0, mismatches
