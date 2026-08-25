"""Predefined standard test scenario definitions and scenario registry."""

from typing import Dict, List, Optional
from skyvanta.core.types import ScenarioEvent, ScenarioEventType, ScenarioOutcome
from skyvanta.simulation.noise import SensorNoiseConfig
from skyvanta.simulation.scenarios import Scenario


class ScenarioRegistry:
    """Registry providing standard predefined engineering test scenarios."""

    _registry: Dict[str, Scenario] = {}

    @classmethod
    def register(cls, scenario: Scenario) -> None:
        """Registers a scenario in the catalog."""
        cls._registry[scenario.scenario_id] = scenario
        cls._registry[scenario.name.lower()] = scenario

    @classmethod
    def get(cls, name_or_id: str) -> Optional[Scenario]:
        """Retrieves a scenario by ID or name."""
        cls._ensure_initialized()
        key = name_or_id.lower()
        return cls._registry.get(key) or cls._registry.get(name_or_id)

    @classmethod
    def list_all(cls) -> List[str]:
        """Lists all registered standard scenario names."""
        cls._ensure_initialized()
        names = []
        for k, v in cls._registry.items():
            if k == v.name.lower():
                names.append(v.name)
        return sorted(names)

    @classmethod
    def get_all_scenarios(cls) -> List[Scenario]:
        """Returns the full suite of unique standard scenarios."""
        cls._ensure_initialized()
        seen = set()
        scenarios = []
        for s in cls._registry.values():
            if s.scenario_id not in seen:
                seen.add(s.scenario_id)
                scenarios.append(s)
        return scenarios

    @classmethod
    def _ensure_initialized(cls) -> None:
        if not cls._registry:
            cls._initialize_standard_scenarios()

    @classmethod
    def _initialize_standard_scenarios(cls) -> None:
        """Initializes the 12 required standard benchmark scenarios."""

        # 1. Nominal Landing
        cls.register(Scenario(
            scenario_id="SCN_NOMINAL_01",
            name="nominal_landing",
            description="Calm nominal vertical descent from 8m to safe touchdown on stationary pad",
            duration_sec=20.0,
            initial_vehicle_pos=(0.1, 0.1, 8.0),
            expected_outcome=ScenarioOutcome.SUCCESS_LANDED,
        ))

        # 2. Target Loss
        cls.register(Scenario(
            scenario_id="SCN_TARGET_LOSS_02",
            name="target_loss",
            description="Normal descent followed by persistent target disappearance triggering climb-out abort",
            duration_sec=15.0,
            initial_vehicle_pos=(0.1, 0.1, 6.0),
            events=[
                ScenarioEvent(
                    event_id="EVT_DISAPPEAR_01",
                    timestamp_sec=4.0,
                    event_type=ScenarioEventType.TARGET_DISAPPEAR,
                    parameters={"duration": 15.0},
                )
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_ABORTED,
        ))

        # 3. Target Occlusion and Recovery
        cls.register(Scenario(
            scenario_id="SCN_TARGET_OCCLUSION_03",
            name="target_occlusion",
            description="Temporary target occlusion at t=3.0s (1.5s duration) with target reacquisition and recovery",
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
        ))

        # 4. Camera Dropout
        cls.register(Scenario(
            scenario_id="SCN_CAMERA_DROPOUT_04",
            name="camera_dropout",
            description="Optical sensor frame stream loss during final descent triggering safe hold/abort",
            duration_sec=15.0,
            initial_vehicle_pos=(0.1, 0.1, 5.0),
            events=[
                ScenarioEvent(
                    event_id="EVT_CAM_DROP_01",
                    timestamp_sec=3.5,
                    duration_sec=10.0,
                    event_type=ScenarioEventType.CAMERA_DROPOUT,
                )
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_ABORTED,
        ))

        # 5. IMU Dropout
        cls.register(Scenario(
            scenario_id="SCN_IMU_DROPOUT_05",
            name="imu_dropout",
            description="Inertial measurement unit dropout during approach triggering safe hold/abort",
            duration_sec=15.0,
            initial_vehicle_pos=(0.1, 0.1, 7.0),
            events=[
                ScenarioEvent(
                    event_id="EVT_IMU_DROP_01",
                    timestamp_sec=3.0,
                    duration_sec=8.0,
                    event_type=ScenarioEventType.IMU_DROPOUT,
                )
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_ABORTED,
        ))

        # 6. Autopilot Disconnect
        cls.register(Scenario(
            scenario_id="SCN_AUTOPILOT_DISCONNECT_06",
            name="autopilot_disconnect",
            description="Autopilot heartbeat loss during descent triggering failsafe command cessation",
            duration_sec=12.0,
            initial_vehicle_pos=(0.1, 0.1, 5.0),
            events=[
                ScenarioEvent(
                    event_id="EVT_AP_DISC_01",
                    timestamp_sec=4.0,
                    duration_sec=10.0,
                    event_type=ScenarioEventType.AUTOPILOT_DISCONNECT,
                )
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_ABORTED,
        ))

        # 7. High Noise
        cls.register(Scenario(
            scenario_id="SCN_HIGH_NOISE_07",
            name="high_noise",
            description="Elevated camera pixel noise and IMU noise simulating severe visual degradation",
            duration_sec=20.0,
            initial_vehicle_pos=(0.1, 0.1, 6.0),
            noise_config=SensorNoiseConfig(
                camera_pixel_sigma=2.5,
                imu_accel_sigma=0.25,
                imu_gyro_sigma=0.03,
                pose_position_sigma=0.08,
            ),
            expected_outcome=ScenarioOutcome.SUCCESS_LANDED,
        ))

        # 8. High Velocity Spike
        cls.register(Scenario(
            scenario_id="SCN_HIGH_VELOCITY_08",
            name="high_velocity",
            description="Sudden lateral velocity disturbance during descent triggering velocity limit checks",
            duration_sec=18.0,
            initial_vehicle_pos=(0.1, 0.1, 6.0),
            events=[
                ScenarioEvent(
                    event_id="EVT_VEL_SPIKE_01",
                    timestamp_sec=3.0,
                    duration_sec=0.5,
                    event_type=ScenarioEventType.VELOCITY_SPIKE,
                    parameters={"impulse_mps": [2.5, 0.0, 0.0]},
                )
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_ABORTED,
        ))

        # 9. High Uncertainty
        cls.register(Scenario(
            scenario_id="SCN_HIGH_UNCERTAINTY_09",
            name="high_uncertainty",
            description="Large sensor noise injection causing 3-sigma covariance envelope exceedance and abort",
            duration_sec=15.0,
            initial_vehicle_pos=(0.1, 0.1, 6.0),
            noise_config=SensorNoiseConfig(
                camera_pixel_sigma=6.0,
                imu_accel_sigma=0.8,
                pose_position_sigma=0.5,
            ),
            expected_outcome=ScenarioOutcome.SUCCESS_ABORTED,
        ))

        # 10. Sensor Timing Failure
        cls.register(Scenario(
            scenario_id="SCN_TIMING_FAILURE_10",
            name="timing_failure",
            description="Stale telemetry frames and timestamp jitter testing temporal synchronization",
            duration_sec=15.0,
            initial_vehicle_pos=(0.1, 0.1, 6.0),
            events=[
                ScenarioEvent(
                    event_id="EVT_TIMING_01",
                    timestamp_sec=2.5,
                    duration_sec=4.0,
                    event_type=ScenarioEventType.POSE_DROPOUT,
                )
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_ABORTED,
        ))

        # 11. Estimator Degradation
        cls.register(Scenario(
            scenario_id="SCN_ESTIMATOR_DEGRADE_11",
            name="estimator_degradation",
            description="Simulated covariance growth and measurement rejection testing filter stability",
            duration_sec=15.0,
            initial_vehicle_pos=(0.1, 0.1, 6.0),
            events=[
                ScenarioEvent(
                    event_id="EVT_EST_DEG_01",
                    timestamp_sec=3.0,
                    duration_sec=6.0,
                    event_type=ScenarioEventType.ESTIMATOR_DEGRADE,
                )
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_ABORTED,
        ))

        # 12. Multiple Simultaneous Failures
        cls.register(Scenario(
            scenario_id="SCN_MULTIPLE_FAILURES_12",
            name="multiple_failures",
            description="Simultaneous optical loss and velocity impulse verifying V7 priority arbitration",
            duration_sec=15.0,
            initial_vehicle_pos=(0.1, 0.1, 6.0),
            events=[
                ScenarioEvent(
                    event_id="EVT_MULTI_01",
                    timestamp_sec=3.0,
                    duration_sec=10.0,
                    event_type=ScenarioEventType.TARGET_DISAPPEAR,
                ),
                ScenarioEvent(
                    event_id="EVT_MULTI_02",
                    timestamp_sec=3.0,
                    duration_sec=0.2,
                    event_type=ScenarioEventType.VELOCITY_SPIKE,
                    parameters={"impulse_mps": [1.8, 1.2, 0.0]},
                ),
            ],
            expected_outcome=ScenarioOutcome.SUCCESS_ABORTED,
        ))
