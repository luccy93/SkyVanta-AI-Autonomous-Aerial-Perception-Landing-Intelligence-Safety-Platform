"""Background subtraction and contrast-based motion candidate detector."""

from typing import List, Optional, Tuple
import cv2
import numpy as np

from skyvanta.core.config import MotionConfig
from skyvanta.core.types import BoundingBox, DetectionSource, MotionCandidate
from skyvanta.perception.motion.base import BaseMotionDetector


class BackgroundSubtractorMotionDetector(BaseMotionDetector):
    """Detects moving target candidates using MOG2 background subtraction and edge density."""

    def __init__(
        self,
        frame_shape: Tuple[int, int],
        config: Optional[any] = None,
    ):
        self.h, self.w = frame_shape[:2]

        if config is None:
            self.config = MotionConfig()
        elif isinstance(config, MotionConfig):
            self.config = config
        elif hasattr(config, "motion") and isinstance(config.motion, MotionConfig):
            self.config = config.motion
        else:
            # Handle legacy DetectorConfig or duck-typed config
            history = getattr(config, "history", getattr(config, "motion_history", 120))
            var_thresh = getattr(config, "var_threshold", getattr(config, "motion_var_threshold", 18.0))
            detect_shadows = getattr(config, "detect_shadows", False)
            min_area = getattr(config, "min_area_ratio", getattr(config, "motion_min_area_ratio", 0.00004))
            max_area = getattr(config, "max_area_ratio", getattr(config, "motion_max_area_ratio", 0.06))
            self.config = MotionConfig(
                history=history,
                var_threshold=var_thresh,
                detect_shadows=detect_shadows,
                min_area_ratio=min_area,
                max_area_ratio=max_area,
            )

        self._bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=self.config.history,
            varThreshold=self.config.var_threshold,
            detectShadows=self.config.detect_shadows,
        )
        self.min_area = max(30, int(self.w * self.h * self.config.min_area_ratio))
        self.max_area = int(self.w * self.h * self.config.max_area_ratio)

    def reset(self) -> None:
        """Re-initializes background subtractor model."""
        self._bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=self.config.history,
            varThreshold=self.config.var_threshold,
            detectShadows=self.config.detect_shadows,
        )

    def detect(self, frame_bgr: np.ndarray) -> List[MotionCandidate]:
        """Detects high-motion and high-contrast bounding box candidates."""
        if not self.config.enabled:
            return []

        h, w = frame_bgr.shape[:2]
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # MOG2 background segmentation
        fg = self._bg_sub.apply(gray_blur, learningRate=0.01)
        _, fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)

        # Edge analysis
        edges = cv2.Canny(gray_blur, 60, 160)
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

        # Morphological cleanup
        combined = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)

        # Apply sky-ground ROI mask (ignore very bottom edge)
        roi_mask = np.zeros_like(combined)
        roi_mask[:int(h * 0.85), :] = 255
        combined = cv2.bitwise_and(combined, roi_mask)

        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates: List[MotionCandidate] = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < self.min_area or area > self.max_area:
                continue
            x, y, cw, ch = cv2.boundingRect(c)
            if ch == 0:
                continue
            aspect = cw / float(ch)
            if aspect < self.config.min_aspect_ratio or aspect > self.config.max_aspect_ratio:
                continue

            roi_edges = edges[y:y + ch, x:x + cw]
            edge_density = float(np.count_nonzero(roi_edges)) / max(1.0, cw * ch)
            raw_score = area * (0.4 + edge_density * self.config.edge_weight)

            # Normalized motion confidence
            norm_conf = min(0.65, 0.40 + (raw_score / 10000.0) * 0.25)

            bbox = BoundingBox(x1=float(x), y1=float(y), x2=float(x + cw), y2=float(y + ch))
            candidates.append(MotionCandidate(
                bbox=bbox,
                motion_score=float(raw_score),
                confidence=float(norm_conf),
                contour_area=float(area),
                edge_density=float(edge_density),
                source=DetectionSource.MOTION,
            ))

        # Sort by raw score descending
        candidates.sort(key=lambda c: c.motion_score, reverse=True)
        return candidates[:5]


# Alias for backward compatibility with V1
MotionContrastDetector = BackgroundSubtractorMotionDetector
