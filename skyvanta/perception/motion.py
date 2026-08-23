"""Motion-contrast and optical flow detector for SkyVanta AI."""

from typing import List, Optional, Tuple
import cv2
import numpy as np
from skyvanta.core.types import Detection, BoundingBox
from skyvanta.core.config import DetectorConfig


class MotionContrastDetector:
    """Detects moving targets via MOG2 background subtraction, Farneback optical flow, and edge analysis."""

    def __init__(self, frame_shape: Tuple[int, int], config: Optional[DetectorConfig] = None):
        self.h, self.w = frame_shape[:2]
        self.config = config or DetectorConfig()
        self.bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=self.config.motion_history,
            varThreshold=self.config.motion_var_threshold,
            detectShadows=False,
        )
        self.prev_gray: Optional[np.ndarray] = None
        self.min_area = max(30, int(self.w * self.h * self.config.motion_min_area_ratio))
        self.max_area = int(self.w * self.h * self.config.motion_max_area_ratio)

    def detect(self, frame_bgr: np.ndarray) -> List[Detection]:
        """Detects high-motion and high-contrast bounding box candidates."""
        h, w = frame_bgr.shape[:2]
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)

        fg = self.bg_sub.apply(gray_blur, learningRate=0.01)
        _, fg = cv2.threshold(fg, 200, 255, cv2.THRESH_BINARY)

        flow_mask = np.zeros_like(gray)
        if self.prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_gray, gray_blur, None, 0.5, 2, 15, 2, 5, 1.1, 0
            )
            mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            mag_n = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX)
            _, flow_mask = cv2.threshold(mag_n.astype(np.uint8), 40, 255, cv2.THRESH_BINARY)
        self.prev_gray = gray_blur

        edges = cv2.Canny(gray_blur, 60, 160)
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

        combined = cv2.bitwise_or(fg, flow_mask)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)

        roi_mask = np.zeros_like(combined)
        roi_mask[:int(h * 0.85), :] = 255
        combined = cv2.bitwise_and(combined, roi_mask)

        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates: List[Tuple[BoundingBox, float]] = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < self.min_area or area > self.max_area:
                continue
            x, y, cw, ch = cv2.boundingRect(c)
            if ch == 0:
                continue
            aspect = cw / float(ch)
            if aspect < 0.25 or aspect > 4.5:
                continue

            roi_edges = edges[y:y + ch, x:x + cw]
            edge_density = float(np.count_nonzero(roi_edges)) / max(1, cw * ch)
            score = area * (0.4 + edge_density * 3.0)
            bbox = BoundingBox(x1=float(x), y1=float(y), x2=float(x + cw), y2=float(y + ch))
            candidates.append((bbox, score))

        candidates.sort(key=lambda item: item[1], reverse=True)
        top_candidates = candidates[:5]

        detections: List[Detection] = []
        for bbox, score in top_candidates:
            norm_conf = min(0.65, 0.45 + (score / 10000.0) * 0.2)
            detections.append(Detection(
                bbox=bbox,
                confidence=norm_conf,
                class_name="motion_target",
                source="motion",
            ))
        return detections
