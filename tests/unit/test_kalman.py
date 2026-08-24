"""Unit tests for 2D constant velocity Kalman filter."""

import pytest
from skyvanta.tracking.kalman import KalmanBox2D


def test_kalman_initialization():
    kf = KalmanBox2D()
    assert not kf.initialized
    kf.init(100.0, 200.0, 50.0, 50.0)
    assert kf.initialized
    cx, cy, w, h = kf.current_state
    assert cx == 100.0
    assert cy == 200.0
    assert w == 50.0
    assert h == 50.0


def test_kalman_predict_correct_cycle():
    kf = KalmanBox2D()
    kf.init(100.0, 100.0, 40.0, 40.0)

    # Move target at +10 px/frame in x
    for i in range(1, 10):
        pred_cx, pred_cy, pred_w, pred_h = kf.predict()
        target_x = 100.0 + i * 10.0
        kf.correct(target_x, 100.0, 40.0, 40.0)

    cx, cy, w, h = kf.current_state
    # Filter should closely track moving target
    assert pytest.approx(cx, abs=5.0) == 190.0
    assert pytest.approx(cy, abs=5.0) == 100.0
    vx, vy = kf.current_velocity
    assert pytest.approx(vx, abs=2.0) == 10.0
    assert pytest.approx(vy, abs=2.0) == 0.0


def test_kalman_noisy_measurement_smoothing():
    kf = KalmanBox2D(process_noise=1e-3, measurement_noise=1e-1)
    kf.init(200.0, 200.0, 50.0, 50.0)

    # Apply alternating noisy measurements around stationary point (200, 200)
    for i in range(20):
        noise = 10.0 if (i % 2 == 0) else -10.0
        kf.predict()
        kf.correct(200.0 + noise, 200.0 + noise, 50.0, 50.0)

    cx, cy, w, h = kf.current_state
    # Filter estimate should remain centered near 200 despite +-10px oscillations
    assert abs(cx - 200.0) < 5.0
    assert abs(cy - 200.0) < 5.0

