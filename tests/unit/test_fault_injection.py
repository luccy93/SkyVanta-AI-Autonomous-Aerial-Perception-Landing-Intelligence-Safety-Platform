"""Unit tests for FaultSchedule and FaultEvent."""

import pytest
from skyvanta.simulation.faults import FaultEvent, FaultSchedule, FaultType


def test_fault_schedule_activation():
    """Verifies that faults activate precisely within their scheduled time window."""
    schedule = FaultSchedule()
    schedule.add_fault(FaultType.OPTICAL_DROPOUT, start_time_sec=2.0, end_time_sec=5.0)

    # Before start
    active, _ = schedule.is_fault_active(FaultType.OPTICAL_DROPOUT, t_sec=1.5)
    assert active is False

    # During window
    active, _ = schedule.is_fault_active(FaultType.OPTICAL_DROPOUT, t_sec=3.0)
    assert active is True

    # After window
    active, _ = schedule.is_fault_active(FaultType.OPTICAL_DROPOUT, t_sec=5.5)
    assert active is False


def test_fault_schedule_parameters():
    """Verifies that fault parameters are passed correctly."""
    schedule = FaultSchedule()
    schedule.add_fault(
        FaultType.REPROJECTION_ERROR_INJECTION,
        start_time_sec=1.0,
        end_time_sec=3.0,
        parameters={"extra_noise": 0.75},
    )

    active, params = schedule.is_fault_active(FaultType.REPROJECTION_ERROR_INJECTION, t_sec=2.0)
    assert active is True
    assert params is not None
    assert params["extra_noise"] == 0.75
