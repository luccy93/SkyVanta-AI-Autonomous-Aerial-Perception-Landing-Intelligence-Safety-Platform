"""Characterization tests verifying numerical and behavioral parity with legacy prototype."""

import pytest
import numpy as np

# Legacy imports
from legacy.main import (
    OneEuroFilter as LegacyOneEuroFilter,
    Vec2EuroFilter as LegacyVec2EuroFilter,
    KalmanBox2D as LegacyKalmanBox2D,
    TelemetryEstimator as LegacyTelemetryEstimator,
)

# New modular imports
from skyvanta.tracking.smoothing import OneEuroFilter, Vec2EuroFilter
from skyvanta.tracking.kalman import KalmanBox2D
from skyvanta.telemetry.estimator import TelemetryEstimator


def test_one_euro_filter_parity():
    legacy_f = LegacyOneEuroFilter(freq=30.0, min_cutoff=1.2, beta=0.02)
    new_f = OneEuroFilter(freq=30.0, min_cutoff=1.2, beta=0.02)

    inputs = [10.0, 12.0, 15.0, 22.0, 35.0, 50.0, 48.0, 45.0, 30.0, 10.0]
    for i, val in enumerate(inputs):
        t = i * (1.0 / 30.0)
        leg_out = legacy_f(val, t=t)
        new_out = new_f(val, t=t)
        assert pytest.approx(leg_out, rel=1e-5) == new_out


def test_vec2_euro_filter_parity():
    legacy_v = LegacyVec2EuroFilter(min_cutoff=1.0, beta=0.015)
    new_v = Vec2EuroFilter(min_cutoff=1.0, beta=0.015)

    points = [(100.0, 200.0), (105.0, 195.0), (110.0, 190.0), (120.0, 180.0)]
    for i, pt in enumerate(points):
        t = i * (1.0 / 30.0)
        leg_pt = legacy_v(pt, t=t)
        new_pt = new_v(pt, t=t)
        assert pytest.approx(leg_pt[0], rel=1e-5) == new_pt[0]
        assert pytest.approx(leg_pt[1], rel=1e-5) == new_pt[1]


def test_kalman_box2d_parity():
    legacy_kf = LegacyKalmanBox2D()
    new_kf = KalmanBox2D()

    legacy_kf.init(300.0, 400.0, 60.0, 50.0)
    new_kf.init(300.0, 400.0, 60.0, 50.0)

    for i in range(1, 15):
        leg_pred = legacy_kf.predict()
        new_pred = new_kf.predict()
        assert pytest.approx(leg_pred, rel=1e-4) == new_pred

        meas = (300.0 + i * 5.0, 400.0 - i * 2.0, 60.0 + i * 0.5, 50.0 + i * 0.5)
        legacy_kf.correct(*meas)
        new_kf.correct(*meas)

        assert pytest.approx(legacy_kf.kf.statePost.flatten(), rel=1e-4) == new_kf.kf.statePost.flatten()


def test_telemetry_estimator_parity():
    legacy_est = LegacyTelemetryEstimator((720, 1280))
    new_est = TelemetryEstimator((720, 1280))

    center = (600.0, 300.0)
    size = (70.0, 40.0)

    for i in range(10):
        t = i * (1.0 / 30.0)
        leg_res = legacy_est.estimate(center, size, track_conf=0.8, scale_trend=0.05, t_sec=t)
        new_res = new_est.estimate(center, size, track_conf=0.8, scale_trend=0.05, t_sec=t)

        assert pytest.approx(leg_res["distance"], rel=1e-4) == new_res.estimated_distance_m
        assert pytest.approx(leg_res["altitude"], rel=1e-4) == new_res.estimated_altitude_m
        assert pytest.approx(leg_res["angle"], rel=1e-4) == new_res.estimated_approach_angle_deg
        assert pytest.approx(leg_res["alignment"], rel=1e-4) == new_res.estimated_alignment_pct
        assert pytest.approx(leg_res["lateral"], rel=1e-4) == new_res.estimated_lateral_offset_m
        assert pytest.approx(leg_res["vertical"], rel=1e-4) == new_res.estimated_vertical_offset_m
        assert pytest.approx(leg_res["landing_confidence"], rel=1e-4) == new_res.landing_confidence_pct
