"""End-to-end integration tests for Volume 8 Flight Interface and Autopilot Integration."""

import pytest

from skyvanta.core.config import FlightInterfaceConfig, LandingIntelligenceConfig
from skyvanta.core.exceptions import FlightInterfaceError
from skyvanta.core.types import (
    CommandStatus,
    FlightCommandType,
    FlightMode,
    LandingPhase,
)
from skyvanta.flight.simulation import FlightSimulationHarness
from skyvanta.intelligence.simulation import LandingScenarioSimulator


def test_end_to_end_nominal_landing_commands():
    """Verifies complete nominal landing sequence produces valid, accepted flight commands."""
    harness = FlightSimulationHarness()

    # Step 1: SEARCHING -> Target not yet acquired -> SEARCH command
    ctx1 = LandingScenarioSimulator.create_context(timestamp_sec=1.0, target_valid=False)
    dec1, cmd1, ack1, telem1 = harness.step(ctx1)
    assert dec1.current_state == LandingPhase.SEARCHING
    assert cmd1.command_type == FlightCommandType.SEARCH
    assert ack1.status == CommandStatus.ACCEPTED

    # Step 2: Target Acquired -> ALIGNING -> ALIGN command
    ctx2 = LandingScenarioSimulator.create_context(timestamp_sec=1.1, target_pos_body=(0.1, 0.1, 10.0))
    dec2, cmd2, ack2, telem2 = harness.step(ctx2)
    assert dec2.current_state == LandingPhase.TARGET_ACQUIRED

    ctx3 = LandingScenarioSimulator.create_context(timestamp_sec=1.2, target_pos_body=(0.1, 0.1, 10.0))
    dec3, cmd3, ack3, telem3 = harness.step(ctx3)
    assert dec3.current_state == LandingPhase.ALIGNING
    assert cmd3.command_type == FlightCommandType.ALIGN
    assert ack3.status == CommandStatus.ACCEPTED

    # Step 3: DESCENDING -> DESCEND command
    # Advance to descending
    harness.fsm._current_phase = LandingPhase.DESCENDING
    ctx4 = LandingScenarioSimulator.create_context(timestamp_sec=1.3, target_pos_body=(0.02, 0.02, 5.0))
    dec4, cmd4, ack4, telem4 = harness.step(ctx4)
    assert dec4.current_state == LandingPhase.DESCENDING
    assert cmd4.command_type == FlightCommandType.DESCEND
    assert ack4.status == CommandStatus.ACCEPTED
    assert telem4.flight_mode == FlightMode.LANDING


def test_target_loss_triggers_abort_command():
    """Verifies that target loss during descent immediately triggers an authorized ABORT command."""
    harness = FlightSimulationHarness()
    harness.fsm._current_phase = LandingPhase.DESCENDING

    # Sudden target dropout at t=2.0
    ctx_lost = LandingScenarioSimulator.create_context(timestamp_sec=2.0, target_valid=False)
    dec, cmd, ack, telem = harness.step(ctx_lost)

    assert dec.current_state == LandingPhase.ABORTING
    assert cmd.command_type == FlightCommandType.ABORT
    assert ack.status == CommandStatus.ACCEPTED
    assert telem.flight_mode == FlightMode.ABORT


def test_autopilot_disconnect_rejects_commands():
    """Verifies that disconnecting the autopilot prevents command execution."""
    harness = FlightSimulationHarness()
    harness.autopilot.disconnect()

    ctx = LandingScenarioSimulator.create_context(timestamp_sec=1.0, target_valid=True)
    dec, cmd, ack, telem = harness.step(ctx)

    assert ack.status == CommandStatus.REJECTED
    assert "DISCONNECTED" in (cmd.rejection_reason or ack.reason)


def test_safety_gate_prevents_unauthorized_external_mode():
    """Verifies that setting mode='external' without allow_external raises FlightInterfaceError."""
    cfg = FlightInterfaceConfig(mode="external")
    cfg.safety.allow_external = False

    with pytest.raises(FlightInterfaceError, match="External autopilot connection rejected"):
        FlightSimulationHarness(flight_config=cfg)
