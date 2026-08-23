"""Unit tests for visual TelemetryEstimator heuristics."""

import pytest
from skyvanta.telemetry.estimator import TelemetryEstimator
from skyvanta.core.config import SkyVantaConfig


def test_telemetry_estimator_none_input():
    estimator = TelemetryEstimator((720, 1280))
    result = estimator.estimate(None, None, 0.5, 0.0, 0.0)
    assert result is None


def test_telemetry_estimator_valid_estimate():
    estimator = TelemetryEstimator((720, 1280))
    center = (640.0, 360.0)
    size = (80.0, 44.0)

    est = estimator.estimate(center, size, track_conf=0.85, scale_trend=0.1, t_sec=0.0)
    assert est is not None
    assert est.estimated_distance_m > 0.0
    assert est.estimated_altitude_m > 0.0
    assert -25.0 <= est.estimated_approach_angle_deg <= 25.0
    assert 0.0 <= est.estimated_alignment_pct <= 100.0
    assert 0.0 <= est.landing_confidence_pct <= 100.0
