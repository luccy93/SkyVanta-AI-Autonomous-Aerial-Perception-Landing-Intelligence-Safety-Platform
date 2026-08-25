"""High-level runner and execution harness for Digital Twin validation."""

from typing import Any, Dict, List, Optional, Tuple

from skyvanta.core.types import ExperimentResult
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.registry import ScenarioRegistry
from skyvanta.simulation.scenarios import Scenario


class DigitalTwinRunner:
    """High-level harness for executing and logging scenarios."""

    def __init__(self, engine: Optional[ScenarioEngine] = None):
        self.engine = engine or ScenarioEngine()

    def run_named_scenario(
        self,
        scenario_name: str,
        seed: Optional[int] = None,
    ) -> Tuple[ExperimentResult, List[Dict[str, Any]]]:
        """Runs a named scenario from the ScenarioRegistry with optional seed override."""
        scenario = ScenarioRegistry.get(scenario_name)
        if scenario is None:
            raise ValueError(f"Unknown scenario name: '{scenario_name}'. Available: {ScenarioRegistry.list_all()}")

        if seed is not None:
            # Create a copy with overridden seed
            scenario_dict = scenario.model_dump()
            scenario_dict["seed"] = int(seed)
            scenario = Scenario(**scenario_dict)

        return self.engine.run(scenario)

    def run_scenario(
        self,
        scenario: Scenario,
        run_id: Optional[str] = None,
    ) -> Tuple[ExperimentResult, List[Dict[str, Any]]]:
        """Runs a Scenario instance directly."""
        return self.engine.run(scenario, run_id=run_id)
