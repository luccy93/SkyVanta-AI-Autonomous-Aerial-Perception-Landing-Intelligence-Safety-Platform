"""6-DoF continuous kinematic vehicle model for Digital Twin simulation."""

import math
from typing import List, Optional, Tuple
import numpy as np

from skyvanta.core.types import (
    DigitalTwinState,
    FlightCommand,
    FlightCommandType,
    TwinVehicleState,
)
from skyvanta.simulation.disturbances import DisturbanceModel
from skyvanta.spatial.transform import (
    euler_to_rotation_matrix,
    rotation_matrix_to_euler,
    rotation_matrix_to_quaternion,
    rotation_matrix_to_rvec,
)


class SimulatedVehicle:
    """Rigid body 6-DoF vehicle kinematic simulation for software validation."""

    def __init__(
        self,
        initial_position: Tuple[float, float, float] = (0.0, 0.0, 8.0),
        initial_velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        initial_euler_deg: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        mass_kg: float = 1.8,
        drag_coefficient: float = 0.25,
    ):
        self.position = np.array(initial_position, dtype=np.float64)
        self.velocity = np.array(initial_velocity, dtype=np.float64)
        self.acceleration = np.zeros(3, dtype=np.float64)
        roll, pitch, yaw = initial_euler_deg
        self.rotation_matrix = euler_to_rotation_matrix(
            math.radians(roll), math.radians(pitch), math.radians(yaw)
        )
        self.angular_velocity = np.zeros(3, dtype=np.float64)
        self.mass_kg = float(mass_kg)
        self.drag_coefficient = float(drag_coefficient)

        # Operational status flags
        self.is_landed: bool = False
        self.touchdown_time_sec: Optional[float] = None
        self.is_armed: bool = True

    @property
    def euler_deg(self) -> Tuple[float, float, float]:
        """Returns Euler angles [roll, pitch, yaw] in degrees."""
        _, deg = rotation_matrix_to_euler(self.rotation_matrix)
        return deg

    @property
    def quaternion(self) -> Tuple[float, float, float, float]:
        """Returns unit quaternion [qw, qx, qy, qz]."""
        return rotation_matrix_to_quaternion(self.rotation_matrix)

    def step(
        self,
        dt_sec: float,
        current_time_sec: float,
        active_command: Optional[FlightCommand] = None,
        target_pad_position: Optional[Tuple[float, float, float]] = None,
        disturbances: Optional[DisturbanceModel] = None,
    ) -> DigitalTwinState:
        """Propagates vehicle kinematics forward by dt_sec with command tracking and disturbances."""
        if dt_sec <= 0.0:
            return self.get_state(current_time_sec)

        pad_pos = np.array(target_pad_position if target_pad_position is not None else (0.0, 0.0, 0.0), dtype=np.float64)

        # 1. Target Desired Velocity from Active Flight Command
        desired_velocity = np.zeros(3, dtype=np.float64)
        target_z = pad_pos[2]

        if active_command is not None and not self.is_landed:
            cmd_type = active_command.command_type

            if cmd_type == FlightCommandType.HOLD:
                desired_velocity = np.array([0.0, 0.0, 0.0], dtype=np.float64)

            elif cmd_type in (FlightCommandType.SEARCH, FlightCommandType.ALIGN):
                err_xy = pad_pos[:2] - self.position[:2]
                v_xy = np.clip(err_xy * 1.5, -1.8, 1.8)
                desired_velocity = np.array([v_xy[0], v_xy[1], 0.0], dtype=np.float64)

            elif cmd_type == FlightCommandType.APPROACH:
                err_xy = pad_pos[:2] - self.position[:2]
                v_xy = np.clip(err_xy * 1.5, -1.5, 1.5)
                # Gentle descent while approaching
                alt = max(0.0, self.position[2] - target_z)
                vz = -0.35 if alt > 3.0 else -0.1
                desired_velocity = np.array([v_xy[0], v_xy[1], vz], dtype=np.float64)

            elif cmd_type == FlightCommandType.DESCEND:
                err_xy = pad_pos[:2] - self.position[:2]
                v_xy = np.clip(err_xy * 1.5, -1.0, 1.0)
                alt = max(0.0, self.position[2] - target_z)
                vz = -np.clip(0.4 * np.sqrt(max(0.1, alt)), 0.15, 0.8)
                desired_velocity = np.array([v_xy[0], v_xy[1], vz], dtype=np.float64)

            elif cmd_type == FlightCommandType.FINAL_APPROACH:
                err_xy = pad_pos[:2] - self.position[:2]
                v_xy = np.clip(err_xy * 1.5, -0.4, 0.4)
                desired_velocity = np.array([v_xy[0], v_xy[1], -0.25], dtype=np.float64)

            elif cmd_type == FlightCommandType.CONFIRM_LANDING:
                desired_velocity = np.array([0.0, 0.0, -0.05], dtype=np.float64)
                if abs(self.position[2] - target_z) < 0.15:
                    self.is_landed = True
                    self.touchdown_time_sec = current_time_sec

            elif cmd_type == FlightCommandType.ABORT:
                desired_velocity = np.array([0.0, 0.0, 1.5], dtype=np.float64)  # Climb out

            elif cmd_type == FlightCommandType.RECOVER:
                desired_velocity = np.array([0.0, 0.0, 0.2], dtype=np.float64)

            elif cmd_type == FlightCommandType.DISARM:
                self.is_armed = False
                desired_velocity = np.array([0.0, 0.0, 0.0], dtype=np.float64)

        # 2. Autopilot Tracking Dynamics (First-Order Lag Tau ~ 0.25s)
        tau = 0.25
        accel_cmd = (desired_velocity - self.velocity) / tau

        # Drag force
        v_rel = self.velocity.copy()
        if disturbances is not None:
            v_rel -= disturbances.constant_wind_mps
        drag_accel = -self.drag_coefficient * v_rel

        # Disturbances
        dist_accel = np.zeros(3, dtype=np.float64)
        if disturbances is not None:
            dist_accel = disturbances.get_net_acceleration_disturbance(current_time_sec)
            # Velocity impulses
            dv = disturbances.check_velocity_impulse(current_time_sec, dt_sec)
            if np.any(dv != 0.0):
                dist_accel += dv / max(1e-6, dt_sec)

        self.acceleration = accel_cmd + drag_accel + dist_accel

        # 3. Integrate Kinematics (Semi-Implicit Euler)
        if not self.is_landed:
            self.velocity += self.acceleration * dt_sec
            self.position += self.velocity * dt_sec

            # Ground plane constraint
            if self.position[2] <= target_z:
                self.position[2] = target_z
                self.velocity[2] = 0.0
                if np.linalg.norm(self.position[:2] - pad_pos[:2]) < 0.5 and abs(self.velocity[2]) < 0.5:
                    self.is_landed = True
                    self.touchdown_time_sec = current_time_sec

        # 4. Attitude Dynamics (tilt with lateral acceleration)
        prev_R = self.rotation_matrix.copy()
        target_pitch = float(np.clip(-self.acceleration[0] * 5.0, -25.0, 25.0))
        target_roll = float(np.clip(self.acceleration[1] * 5.0, -25.0, 25.0))
        target_yaw = 0.0
        new_R = euler_to_rotation_matrix(
            math.radians(target_roll), math.radians(target_pitch), math.radians(target_yaw)
        )
        self.rotation_matrix = new_R

        # Kinematic angular rate from rotation matrix differential: dR = R * [omega]_x * dt
        # R_rel = prev_R^T @ new_R
        R_rel = prev_R.T @ new_R
        rvec = rotation_matrix_to_rvec(R_rel)
        omega_kinematic = rvec / max(1e-6, dt_sec)

        # Angular rate disturbance
        if disturbances is not None:
            self.angular_velocity = omega_kinematic + disturbances.get_angular_disturbance(current_time_sec)
        else:
            self.angular_velocity = omega_kinematic

        return self.get_state(current_time_sec)

    def get_state(self, timestamp_sec: float) -> DigitalTwinState:
        """Constructs a strongly-typed DigitalTwinState snapshot."""
        return DigitalTwinState(
            timestamp_sec=float(timestamp_sec),
            position_world=tuple(float(x) for x in self.position),
            velocity_world=tuple(float(x) for x in self.velocity),
            acceleration_world=tuple(float(x) for x in self.acceleration),
            rotation_matrix=self.rotation_matrix.tolist(),
            quaternion=self.quaternion,
            euler_deg=self.euler_deg,
            angular_velocity_body=tuple(float(x) for x in self.angular_velocity),
            is_landed=self.is_landed,
        )

    def reset(
        self,
        position: Tuple[float, float, float] = (0.0, 0.0, 8.0),
        velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> None:
        """Resets the vehicle state."""
        self.position = np.array(position, dtype=np.float64)
        self.velocity = np.array(velocity, dtype=np.float64)
        self.acceleration = np.zeros(3, dtype=np.float64)
        self.rotation_matrix = np.eye(3, dtype=np.float64)
        self.angular_velocity = np.zeros(3, dtype=np.float64)
        self.is_landed = False
        self.touchdown_time_sec = None
        self.is_armed = True
