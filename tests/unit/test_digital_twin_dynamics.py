"""Unit tests for DroneDynamics6DoF."""

import numpy as np
import pytest

from skyvanta.core.types import CommandSource, FlightCommand, FlightCommandType
from skyvanta.simulation.dynamics import DroneDynamics6DoF


def test_dynamics_initial_state():
    """Verifies initial vehicle position and velocity."""
    dyn = DroneDynamics6DoF(initial_position=(0.0, 0.0, 10.0))
    state = dyn.get_state()
    assert state.position_world == (0.0, 0.0, 10.0)
    assert state.velocity_world == (0.0, 0.0, 0.0)
    assert state.is_landed is False


def test_dynamics_step_descend():
    """Verifies descent command reduces vehicle altitude."""
    dyn = DroneDynamics6DoF(initial_position=(0.0, 0.0, 10.0))
    cmd = FlightCommand(
        command_id="CMD_001",
        sequence_number=1,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.DESCEND,
        source=CommandSource.LANDING_INTELLIGENCE,
    )
    wind = np.zeros(3)

    for _ in range(20):  # 1.0s at dt=0.05
        state = dyn.step(dt=0.05, active_command=cmd, wind_velocity=wind)

    assert state.position_world[2] < 10.0
    assert state.velocity_world[2] < 0.0


def test_dynamics_step_abort_climb():
    """Verifies abort command causes vehicle to climb."""
    dyn = DroneDynamics6DoF(initial_position=(0.0, 0.0, 5.0))
    cmd = FlightCommand(
        command_id="CMD_002",
        sequence_number=2,
        timestamp_sec=1.0,
        expiration_sec=1.5,
        command_type=FlightCommandType.ABORT,
        source=CommandSource.SAFETY_SUPERVISOR,
    )
    wind = np.zeros(3)

    for _ in range(20):  # 1.0s
        state = dyn.step(dt=0.05, active_command=cmd, wind_velocity=wind)

    assert state.position_world[2] > 5.0
    assert state.velocity_world[2] > 0.0
