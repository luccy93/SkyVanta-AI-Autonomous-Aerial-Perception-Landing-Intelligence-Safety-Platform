"""2D constant-velocity Kalman filter for bounding boxes."""

from typing import Tuple
import cv2
import numpy as np


class KalmanBox2D:
    """8-state, 4-measurement linear Kalman filter tracking (cx, cy, w, h, vx, vy, vw, vh)."""

    def __init__(self, process_noise: float = 1e-2, measurement_noise: float = 1e-1):
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
        self.kf.processNoiseCov = np.eye(8, dtype=np.float32) * process_noise
        self.kf.measurementNoiseCov = np.eye(4, dtype=np.float32) * measurement_noise
        self.kf.errorCovPost = np.eye(8, dtype=np.float32)
        self.initialized = False

    def init(self, cx: float, cy: float, w: float, h: float) -> None:
        """Initializes state with first detection measurement."""
        self.kf.statePost = np.array([[cx], [cy], [w], [h], [0], [0], [0], [0]], dtype=np.float32)
        self.initialized = True

    def predict(self) -> Tuple[float, float, float, float]:
        """Propagates state forward by dt."""
        s = self.kf.predict().flatten()
        return float(s[0]), float(s[1]), float(s[2]), float(s[3])

    def correct(self, cx: float, cy: float, w: float, h: float) -> None:
        """Updates state with incoming measurement."""
        meas = np.array([[cx], [cy], [w], [h]], dtype=np.float32)
        self.kf.correct(meas)

    @property
    def current_state(self) -> Tuple[float, float, float, float]:
        """Returns the current filtered state (cx, cy, w, h)."""
        s = self.kf.statePost.flatten()
        return float(s[0]), float(s[1]), float(s[2]), float(s[3])
