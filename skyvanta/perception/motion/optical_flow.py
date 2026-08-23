"""Dense optical flow computation and motion vector field analysis."""

import math
from typing import Optional, Tuple
import cv2
import numpy as np

from skyvanta.core.config import OpticalFlowConfig
from skyvanta.core.types import BoundingBox, OpticalFlowResult


class FarnebackOpticalFlow:
    """Computes two-frame dense optical flow using Gunnar Farneback's algorithm."""

    def __init__(self, config: Optional[OpticalFlowConfig] = None):
        self.config = config or OpticalFlowConfig()
        self._prev_gray: Optional[np.ndarray] = None

    def reset(self) -> None:
        """Resets stored previous grayscale frame."""
        self._prev_gray = None

    def compute(self, frame_bgr: np.ndarray) -> OpticalFlowResult:
        """Calculates optical flow relative to the previous frame.

        Handles first frame, low texture, and sudden motion discontinuities safely.
        """
        if not self.config.enabled:
            return OpticalFlowResult(has_significant_motion=False)

        if frame_bgr is None or frame_bgr.size == 0:
            return OpticalFlowResult(has_significant_motion=False)

        # Convert to grayscale and blur
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)

        if self._prev_gray is None or self._prev_gray.shape != gray_blur.shape:
            self._prev_gray = gray_blur
            return OpticalFlowResult(has_significant_motion=False)

        # Compute dense optical flow
        try:
            flow = cv2.calcOpticalFlowFarneback(
                self._prev_gray,
                gray_blur,
                None,
                pyr_scale=self.config.pyr_scale,
                levels=self.config.levels,
                winsize=self.config.winsize,
                iterations=self.config.iterations,
                poly_n=self.config.poly_n,
                poly_sigma=self.config.poly_sigma,
                flags=0,
            )
        except Exception:
            self._prev_gray = gray_blur
            return OpticalFlowResult(has_significant_motion=False)

        self._prev_gray = gray_blur

        # Calculate Cartesian to polar coordinates (magnitude & angle in degrees)
        fx, fy = flow[..., 0], flow[..., 1]
        mag, ang = cv2.cartToPolar(fx, fy, angleInDegrees=True)

        mean_mag = float(np.mean(mag))
        max_mag = float(np.max(mag))

        # Check if flow magnitude exceeds noise floor
        has_motion = mean_mag > 0.5 or max_mag > 3.0

        # Dominant motion direction
        dominant_angle = float(np.median(ang[mag > 1.0])) if np.any(mag > 1.0) else 0.0

        return OpticalFlowResult(
            mean_magnitude=mean_mag,
            max_magnitude=max_mag,
            motion_direction_deg=dominant_angle,
            has_significant_motion=has_motion,
        )

    def extract_roi_flow_energy(self, bbox: BoundingBox, frame_shape: Tuple[int, int]) -> float:
        """Estimates normalized optical flow energy in a specific bounding box ROI [0.0, 1.0]."""
        if self._prev_gray is None:
            return 0.0
        h, w = frame_shape[:2]
        clipped = bbox.clip(max_width=w, max_height=h)
        if not clipped.is_valid():
            return 0.0

        x1, y1, x2, y2 = clipped.to_int_tuple()
        roi_prev = self._prev_gray[y1:y2, x1:x2]
        if roi_prev.size == 0 or roi_prev.shape[0] < 4 or roi_prev.shape[1] < 4:
            return 0.0

        # Fast gradient approximation as flow surrogate
        std_val = float(np.std(roi_prev))
        return min(1.0, std_val / 64.0)
