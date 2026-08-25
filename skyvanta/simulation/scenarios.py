"""Scenario data model, configuration specification, and fingerprint hashing."""

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from skyvanta.core.types import ScenarioEvent, ScenarioOutcome
from skyvanta.simulation.latency import SubsystemLatencyConfig
from skyvanta.simulation.noise import SensorNoiseConfig


class Scenario(BaseModel):
    """Declarative specification of an automated landing simulation scenario."""
    scenario_id: str = Field(..., description="Unique scenario identifier (e.g. SCN_NOMINAL_01)")
    name: str = Field(..., description="Human-readable scenario name")
    description: str = Field(default="", description="Detailed test scenario description")
    duration_sec: float = Field(default=20.0, gt=0.0, description="Maximum simulation execution timeout in seconds")
    timestep_sec: float = Field(default=0.05, gt=0.0, description="Simulation discrete integration timestep in seconds")
    seed: int = Field(default=42, description="Deterministic pseudo-random generator seed")

    initial_vehicle_pos: Tuple[float, float, float] = Field(default=(0.1, 0.1, 8.0), description="Initial vehicle position [x, y, z] in meters")
    initial_vehicle_vel: Tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0), description="Initial vehicle velocity [vx, vy, vz] in m/s")
    initial_vehicle_euler_deg: Tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0), description="Initial vehicle attitude [roll, pitch, yaw] in degrees")

    target_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "marker_size_m": 0.8,
            "initial_position": [0.0, 0.0, 0.0],
            "velocity_mps": [0.0, 0.0, 0.0],
            "target_id": 1,
        },
        description="Landing target platform kinematic parameters"
    )

    sensor_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "camera_fps": 30.0,
            "imu_rate_hz": 100.0,
        },
        description="Sensor hardware capture rates"
    )

    noise_config: SensorNoiseConfig = Field(default_factory=SensorNoiseConfig, description="Sensor noise parameters")
    latency_config: SubsystemLatencyConfig = Field(default_factory=SubsystemLatencyConfig, description="Subsystem latency parameters")
    fault_config: Dict[str, Any] = Field(default_factory=dict, description="Pre-scheduled fault configurations")
    disturbance_config: Dict[str, Any] = Field(default_factory=dict, description="Environmental and wind disturbance configuration")

    expected_outcome: ScenarioOutcome = Field(default=ScenarioOutcome.SUCCESS_LANDED, description="Expected scenario pass criteria")
    events: List[ScenarioEvent] = Field(default_factory=list, description="List of time-scheduled perturbation events")

    @property
    def initial_drone_pos(self) -> Tuple[float, float, float]:
        """Alias for initial_vehicle_pos for test compatibility."""
        return self.initial_vehicle_pos


def compute_configuration_hash(scenario: Scenario) -> str:
    """Computes a deterministic SHA-256 fingerprint of the entire scenario configuration."""
    data = {
        "scenario_id": scenario.scenario_id,
        "name": scenario.name,
        "duration_sec": scenario.duration_sec,
        "timestep_sec": scenario.timestep_sec,
        "seed": scenario.seed,
        "initial_vehicle_pos": scenario.initial_vehicle_pos,
        "initial_vehicle_vel": scenario.initial_vehicle_vel,
        "target_config": scenario.target_config,
        "sensor_config": scenario.sensor_config,
        "noise_config": scenario.noise_config.model_dump(),
        "latency_config": scenario.latency_config.model_dump(),
        "fault_config": scenario.fault_config,
        "disturbance_config": scenario.disturbance_config,
        "expected_outcome": scenario.expected_outcome.value,
        "events": [e.model_dump() for e in scenario.events],
    }
    encoded = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


ScenarioDefinition = Scenario


class ScenarioCatalog:
    """Catalog mapping for scenario lookup and standard suite instantiation."""

    @staticmethod
    def nominal_descent() -> Scenario:
        return Scenario(
            scenario_id="SCN_NOMINAL_01",
            name="NOMINAL_VERTICAL_DESCENT",
            description="Calm nominal vertical descent from 8m to safe touchdown on stationary pad",
            duration_sec=20.0,
            initial_vehicle_pos=(0.1, 0.1, 8.0),
            expected_outcome=ScenarioOutcome.SUCCESS_LANDED,
        )

    @staticmethod
    def turbulent_crosswind() -> Scenario:
        from skyvanta.core.types import ScenarioEventType
        return Scenario(
            scenario_id="SCN_CROSSWIND_02",
            name="TURBULENT_CROSSWIND_DESCENT",
            description="Descent under turbulent crosswind gusts",
            duration_sec=20.0,
            initial_vehicle_pos=(0.1, 0.1, 6.0),
            noise_config=SensorNoiseConfig(
                camera_pixel_sigma=2.0,
                imu_accel_sigma=0.2,
            ),
            events=[
                ScenarioEvent(
                    event_id="EVT_WIND_01",
                    timestamp_sec=2.0,
                    duration_sec=3.0,
                    event_type=ScenarioEventType.WIND_DISTURBANCE,
                    parameters={"force_mps2": [1.5, 0.5]},
                )
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_LANDED,
        )

    @staticmethod
    def optical_occlusion_abort() -> Scenario:
        from skyvanta.core.types import ScenarioEventType
        return Scenario(
            scenario_id="SCN_OCCLUSION_ABORT_03",
            name="OPTICAL_OCCLUSION_ABORT",
            description="Persistent optical occlusion triggering climb-out abort",
            duration_sec=15.0,
            initial_vehicle_pos=(0.1, 0.1, 6.0),
            events=[
                ScenarioEvent(
                    event_id="EVT_DISAPPEAR_01",
                    timestamp_sec=3.0,
                    duration_sec=12.0,
                    event_type=ScenarioEventType.TARGET_DISAPPEAR,
                )
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_ABORTED,
        )

    @staticmethod
    def target_reacquisition_recovery() -> Scenario:
        from skyvanta.core.types import ScenarioEventType
        return Scenario(
            scenario_id="SCN_TARGET_REACQ_04",
            name="TARGET_REACQUISITION_RECOVERY",
            description="Temporary target occlusion with successful reacquisition and recovery",
            duration_sec=22.0,
            initial_vehicle_pos=(0.1, 0.1, 7.0),
            events=[
                ScenarioEvent(
                    event_id="EVT_OCCLUDE_01",
                    timestamp_sec=3.0,
                    duration_sec=1.5,
                    event_type=ScenarioEventType.TARGET_OCCLUDE,
                )
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_RECOVERED,
        )

    @staticmethod
    def low_visibility_high_noise() -> Scenario:
        return Scenario(
            scenario_id="SCN_HIGH_NOISE_05",
            name="LOW_VISIBILITY_HIGH_NOISE",
            description="Elevated sensor noise simulating severe atmospheric degradation",
            duration_sec=20.0,
            initial_vehicle_pos=(0.1, 0.1, 6.0),
            noise_config=SensorNoiseConfig(
                camera_pixel_sigma=2.5,
                imu_accel_sigma=0.25,
                pose_position_sigma=0.08,
            ),
            expected_outcome=ScenarioOutcome.SUCCESS_LANDED,
        )

    @staticmethod
    def moving_landing_pad() -> Scenario:
        return Scenario(
            scenario_id="SCN_MOVING_PAD_06",
            name="MOVING_LANDING_PAD",
            description="Landing pad in steady linear motion",
            duration_sec=20.0,
            initial_vehicle_pos=(0.1, 0.1, 8.0),
            target_config={
                "marker_size_m": 0.8,
                "initial_position": [0.0, 0.0, 0.0],
                "velocity_mps": [0.2, 0.0, 0.0],
                "target_id": 1,
            },
            expected_outcome=ScenarioOutcome.SUCCESS_LANDED,
        )

    @classmethod
    def get_full_suite(cls) -> List[Scenario]:
        return [
            cls.nominal_descent(),
            cls.turbulent_crosswind(),
            cls.optical_occlusion_abort(),
            cls.target_reacquisition_recovery(),
            cls.low_visibility_high_noise(),
            cls.moving_landing_pad(),
        ]

