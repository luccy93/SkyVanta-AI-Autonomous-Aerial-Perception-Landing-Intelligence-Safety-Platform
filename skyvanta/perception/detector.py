"""YOLO-based drone and target object detector for SkyVanta AI."""

from typing import List, Optional
import numpy as np
from skyvanta.core.types import Detection, BoundingBox
from skyvanta.core.config import DetectorConfig
from skyvanta.core.logging import get_logger

logger = get_logger("skyvanta.perception.detector")

try:
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False


class YoloDroneDetector:
    """YOLOv8-based aerial target detector."""

    def __init__(self, config: Optional[DetectorConfig] = None):
        self.config = config or DetectorConfig()
        self.is_available = False
        self.model = None

        if not self.config.use_yolo:
            logger.info("YOLO detector disabled by configuration.")
            return

        if not _YOLO_AVAILABLE:
            logger.warning("Ultralytics package is not installed. YOLO detector disabled (fallback only).")
            return

        try:
            self.model = YOLO(self.config.yolo_model_path)
            self.is_available = True
            logger.info("YOLO model '%s' loaded successfully.", self.config.yolo_model_path)
        except Exception as e:
            logger.warning("Could not load YOLO model '%s': %s (fallback only)", self.config.yolo_model_path, e)
            self.is_available = False

    def detect(self, frame_bgr: np.ndarray, confidence_threshold: Optional[float] = None) -> List[Detection]:
        """Runs object detection inference on a BGR video frame."""
        if not self.is_available or self.model is None:
            return []

        conf = confidence_threshold or self.config.yolo_confidence_threshold
        try:
            results = self.model.predict(
                frame_bgr,
                verbose=False,
                conf=conf,
                imgsz=self.config.yolo_input_size,
            )
        except Exception as e:
            logger.debug("YOLO inference failed on frame: %s", e)
            return []

        detections: List[Detection] = []
        for r in results:
            for b in r.boxes:
                cls_id = int(b.cls[0])
                name = self.model.names.get(cls_id, "")
                if name not in self.config.yolo_accept_classes:
                    continue
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                bbox = BoundingBox(x1=float(x1), y1=float(y1), x2=float(x2), y2=float(y2))
                detections.append(Detection(
                    bbox=bbox,
                    confidence=float(b.conf[0]),
                    class_name=name,
                    source="yolo",
                ))
        return detections
