"""6-DoF continuous rigid-body vehicle kinematics and dynamics simulator."""

import math
from typing import List, Optional, Tuple
import numpy as np

from skyvanta.core.types import (
    FlightCommand,
    FlightCommandType,
    TwinVehicleState,
)
from skyvanta.spatial.transform import rotation_matrix_to_euler


class DroneDynamics6DoF:
    """Simulates 6-DoF vehicle kinematics, wind aerodynamic drag, and flight directive tracking."""

    def __init__(
        self,
        initial_position: Tuple[float, float, float] = (0.0, 0.0, 10.0),
        initial_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        mass_kg: float = 1.5,
        drag_coeff: float = 0.2,
    ):
        self.mass_kg = mass_kg
        self.drag_coeff = drag_coeff

        self.position = np.array(initial_position, dtype=np.float64)
        self.velocity = np.array(initial_velocity, dtype=np.float64)
        self.rotation_matrix = np.eye(3, dtype=np.float64)
        self.angular_velocity = np.zeros(3, dtype=np.float64)
        self.timestamp_sec: float = 0.0
        self.is_landed: bool = False

    def step(
        self,
        dt: float,
        active_command: Optional[FlightCommand],
        wind_velocity: np.ndarray,
        target_pad_position: np.ndarray = np.zeros(3),
    ) -> TwinVehicleState:
        """Integrates vehicle state over duration dt."""
        if self.is_landed:
            self.velocity = np.zeros(3)
            return self.get_state()

        self.timestamp_sec += dt

        # Determine target velocity based on flight command directive
        target_vel = np.zeros(3, dtype=np.float64)

        if active_command is not None:
            cmd = active_command.command_type
            if cmd == FlightCommandType.DESCEND:
                # Controlled descent toward target position (X, Y centering + Z descent)
                error_xy = target_pad_position[:2] - self.position[:2]
                v_xy = np.clip(0.5 * error_xy, -1.0, 1.0)
                target_vel = np.array([v_xy[0], v_xy[1], -0.5], dtype=np.float64)

            elif cmd == FlightCommandType.FINAL_APPROACH:
                error_xy = target_pad_position[:2] - self.position[:2]
                v_xy = np.clip(0.3 * error_xy, -0.3, 0.3)
                target_vel = np.array([v_xy[0], v_xy[1], -0.2], dtype=np.float64)

            elif cmd == FlightCommandType.ABORT:
                # Climb out away from ground at 1.0 m/s
                target_vel = np.array([0.0, 0.0, 1.0], dtype=np.float64)

            elif cmd == FlightCommandType.ALIGN:
                error_xy = target_pad_position[:2] - self.position[:2]
                v_xy = np.clip(0.4 * error_xy, -0.8, 0.8)
                target_vel = np.array([v_xy[0], v_xy[1], 0.0], dtype=np.float64)

            elif cmd == FlightCommandType.HOLD:
                target_vel = np.zeros(3, dtype=np.float64)

            elif cmd == FlightCommandType.CONFIRM_LANDING:
                self.is_landed = True
                self.velocity = np.zeros(3)
                self.position[2] = target_pad_position[2]
                return self.get_state()

        # Closed-loop velocity tracking controller with first-order lag
        time_constant = 0.3  # seconds
        accel_cmd = (target_vel - self.velocity) / time_constant

        # Relative airspeed & aerodynamic drag
        relative_wind = self.velocity - wind_velocity
        drag_force = -self.drag_coeff * relative_wind * np.linalg.norm(relative_wind)
        accel_total = accel_cmd + drag_force / self.mass_kg

        # Kinematic integration
        self.velocity += accel_total * dt
        self.position += self.velocity * dt

        # Enforce ground contact
        if self.position[2] <= target_pad_position[2] and self.position[2] >= 0.0:
            if active_command and active_command.command_type in (
                FlightCommandType.FINAL_APPROACH,
                FlightCommandType.CONFIRM_LANDING,
            ):
                self.position[2] = target_pad_position[2]
                self.velocity = np.zeros(3)

        return self.get_state()

    def get_state(self) -> TwinVehicleState:
        """Returns the current TwinVehicleState snapshot."""
        euler_rad, euler_deg = rotation_matrix_to_euler(self.rotation_matrix)
        return TwinVehicleState(
            timestamp_sec=self.timestamp_sec,
            position_world=(float(self.position[0]), float(self.position[1]), float(self.position[2])),
            velocity_world=(float(self.velocity[0]), float(self.velocity[1]), float(self.velocity[2])),
            rotation_matrix=self.rotation_matrix.tolist(),
            euler_deg=euler_deg,
            angular_velocity_rad_s=(
                float(self.angular_velocity[0]),
                float(self.angular_velocity[1]),
                float(self.angular_velocity[2]),
            ),
            is_landed=self.is_landed,
        )
