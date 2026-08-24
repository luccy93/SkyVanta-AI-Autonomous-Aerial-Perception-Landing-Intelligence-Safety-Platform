"""2D constant-velocity linear Kalman filter for bounding boxes."""

from typing import Optional, Tuple
import cv2
import numpy as np


class KalmanBox2D:
    """8-state linear Kalman filter tracking bounding box state and velocity:
    State: [cx, cy, w, h, vx, vy, vw, vh]^T
    Measurement: [cx, cy, w, h]^T
    """

    def __init__(self, process_noise: float = 1e-2, measurement_noise: float = 1e-1):
        self.process_noise = float(process_noise)
        self.measurement_noise = float(measurement_noise)
        self.kf = cv2.KalmanFilter(8, 4)
        dt = 1.0
        self.kf.transitionMatrix = np.array([
            [1, 0, 0, 0, dt, 0, 0, 0],
            [0, 1, 0, 0, 0, dt, 0, 0],
            [0, 0, 1, 0, 0, 0, dt, 0],
            [0, 0, 0, 1, 0, 0, 0, dt],
            [0, 0, 0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 0, 1],
        ], dtype=np.float32)
        self.kf.measurementMatrix = np.eye(4, 8, dtype=np.float32)
        self.kf.processNoiseCov = np.eye(8, dtype=np.float32) * self.process_noise
        self.kf.measurementNoiseCov = np.eye(4, dtype=np.float32) * self.measurement_noise
        self.kf.errorCovPost = np.eye(8, dtype=np.float32)
        self.initialized = False

    def init(self, cx: float, cy: float, w: float, h: float) -> None:
        """Initializes filter state with first observed measurement."""
        self.kf.statePost = np.array([[cx], [cy], [w], [h], [0], [0], [0], [0]], dtype=np.float32)
        self.kf.errorCovPost = np.eye(8, dtype=np.float32)
        self.initialized = True

    def predict(self) -> Tuple[float, float, float, float]:
        """Propagates state forward in time using constant velocity model."""
        if not self.initialized:
            return (0.0, 0.0, 0.0, 0.0)
        s = self.kf.predict().flatten()
        return float(s[0]), float(s[1]), max(4.0, float(s[2])), max(4.0, float(s[3]))

    def correct(self, cx: float, cy: float, w: float, h: float) -> Tuple[float, float, float, float]:
        """Updates internal state estimate with incoming measurement."""
        if not self.initialized:
            self.init(cx, cy, w, h)
            return (cx, cy, w, h)
        meas = np.array([[cx], [cy], [w], [h]], dtype=np.float32)
        s = self.kf.correct(meas).flatten()
        return float(s[0]), float(s[1]), max(4.0, float(s[2])), max(4.0, float(s[3]))

    @property
    def current_state(self) -> Tuple[float, float, float, float]:
        """Returns the current filtered state (cx, cy, w, h)."""
        if not self.initialized:
            return (0.0, 0.0, 0.0, 0.0)
        s = self.kf.statePost.flatten()
        return float(s[0]), float(s[1]), max(4.0, float(s[2])), max(4.0, float(s[3]))

    @property
    def current_velocity(self) -> Tuple[float, float]:
        """Returns current estimated velocity (vx, vy) in pixels/frame."""
        if not self.initialized:
            return (0.0, 0.0)
        s = self.kf.statePost.flatten()
        return float(s[4]), float(s[5])
