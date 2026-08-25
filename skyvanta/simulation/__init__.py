"""SkyVanta AI — Volume 9 Digital Twin, Advanced Simulation & Scenario Validation."""

from skyvanta.simulation.benchmark import SimulationBenchmark
from skyvanta.simulation.camera import SimulatedCamera
from skyvanta.simulation.clock import SimulationClock
from skyvanta.simulation.disturbances import DisturbanceEvent, DisturbanceModel
from skyvanta.simulation.dropout import (
    FrameDropoutModel,
    FrameDropoutType,
    OcclusionModel,
    OcclusionType,
    SensorFaultModel,
    SensorFaultType,
    SensorType,
)
from skyvanta.simulation.engine import ScenarioEngine
from skyvanta.simulation.imu import SimulatedIMU
from skyvanta.simulation.latency import LatencyModel, SubsystemLatencyConfig
from skyvanta.simulation.monte_carlo import MonteCarloRunner
from skyvanta.simulation.noise import (
    BiasNoise,
    GaussianNoise,
    RandomWalkNoise,
    SensorNoiseConfig,
    UniformNoise,
)
from skyvanta.simulation.registry import ScenarioRegistry
from skyvanta.simulation.replay import ScenarioReplay
from skyvanta.simulation.reports import ScenarioReportGenerator
from skyvanta.simulation.runner import DigitalTwinRunner
from skyvanta.simulation.safety import SafetyViolationDetector
from skyvanta.simulation.scenarios import Scenario, compute_configuration_hash
from skyvanta.simulation.synthetic import (
    SyntheticSceneGenerator,
    apply_zoom_pan,
    generate_synthetic_background,
)
from skyvanta.simulation.target import SimulatedLandingTarget
from skyvanta.simulation.vehicle import SimulatedVehicle

# Compatibility aliases
DigitalTwinEngine = ScenarioEngine

__all__ = [
    "SimulationClock",
    "SimulatedVehicle",
    "SimulatedLandingTarget",
    "SimulatedCamera",
    "SimulatedIMU",
    "GaussianNoise",
    "BiasNoise",
    "RandomWalkNoise",
    "UniformNoise",
    "SensorNoiseConfig",
    "LatencyModel",
    "SubsystemLatencyConfig",
    "FrameDropoutModel",
    "FrameDropoutType",
    "SensorFaultModel",
    "SensorFaultType",
    "SensorType",
    "OcclusionModel",
    "OcclusionType",
    "DisturbanceModel",
    "DisturbanceEvent",
    "SafetyViolationDetector",
    "Scenario",
    "ScenarioRegistry",
    "compute_configuration_hash",
    "ScenarioEngine",
    "DigitalTwinEngine",
    "DigitalTwinRunner",
    "MonteCarloRunner",
    "ScenarioReplay",
    "SimulationBenchmark",
    "ScenarioReportGenerator",
    "SyntheticSceneGenerator",
    "generate_synthetic_background",
    "apply_zoom_pan",
]
