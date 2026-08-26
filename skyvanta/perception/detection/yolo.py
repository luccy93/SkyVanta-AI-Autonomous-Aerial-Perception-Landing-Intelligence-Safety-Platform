"""Production YOLO-based object detector implementation."""

from typing import Any, Dict, List, Optional
import os
import numpy as np

from skyvanta.core.config import DetectorConfig
from skyvanta.core.exceptions import ModelLoadError
from skyvanta.core.logging import get_logger
from skyvanta.core.types import BoundingBox, Detection, DetectionSource
from skyvanta.perception.detection.base import BaseDetector
from skyvanta.perception.detection.parser import DetectionParser

logger = get_logger("skyvanta.perception.detection.yolo")

try:
    from ultralytics import YOLO
    _ULTRALYTICS_AVAILABLE = True
except ImportError:
    _ULTRALYTICS_AVAILABLE = False


class YoloDroneDetector(BaseDetector):
    """YOLOv8 deep learning aerial target detector."""

    def __init__(self, config: Optional[DetectorConfig] = None, strict: bool = False):
        self.config = config or DetectorConfig()
        self._model = None
        self._is_available = False

        if not self.config.use_yolo:
            logger.info("YOLO detector disabled via configuration.")
            return

        if not _ULTRALYTICS_AVAILABLE:
            msg = (
                "The 'ultralytics' package is not installed. "
                "YOLO detection is unavailable. Install with 'pip install ultralytics' "
                "or run in motion-only mode (--no-yolo)."
            )
            if strict:
                raise ModelLoadError(msg)
            logger.warning(msg)
            return

        model_path = self.config.yolo_model_path
        allow_download = getattr(self.config, "allow_network_download", False)

        # Strictly enforce offline execution and local model availability
        if not allow_download:
            if not model_path or not os.path.isfile(model_path):
                msg = (
                    f"Local YOLO weights file not found at '{model_path}' and allow_network_download is False. "
                    f"SkyVanta prohibits automatic runtime network downloads. "
                    f"Provide an authentic local weights file path or run in motion-only mode (--no-yolo)."
                )
                if strict:
                    raise ModelLoadError(msg)
                logger.warning("%s (Falling back to motion contrast)", msg)
                self._is_available = False
                return

        try:
            # Load YOLO model
            self._model = YOLO(model_path)
            self._is_available = True
            logger.info("Loaded YOLO model from '%s' on device '%s'.", model_path, self.config.yolo_device)
        except Exception as e:
            msg = (
                f"Failed to load YOLO model weights from '{model_path}'. "
                f"Ensure the weight file exists and is accessible, or configure "
                f"'perception.detector.yolo_model_path' in your config YAML. Error details: {e}"
            )
            if strict:
                raise ModelLoadError(msg) from e
            logger.warning("%s (Falling back to motion contrast)", msg)
            self._is_available = False

    @property
    def is_available(self) -> bool:
        return self._is_available

    @property
    def ok(self) -> bool:
        """Legacy compatibility alias for is_available."""
        return self._is_available

    def detect(
        self,
        frame_bgr: np.ndarray,
        confidence_threshold: Optional[float] = None,
        frame_id: Optional[int] = None,
        timestamp_sec: Optional[float] = None,
    ) -> List[Detection]:
        """Performs forward inference on a BGR video frame."""
        if not self._is_available or self._model is None:
            return []

        conf = confidence_threshold or self.config.yolo_confidence_threshold
        try:
            results = self._model.predict(
                frame_bgr,
                verbose=False,
                conf=conf,
                iou=self.config.yolo_iou_threshold,
                imgsz=self.config.yolo_input_size,
                device=self.config.yolo_device if self.config.yolo_device != "cpu" else None,
            )
        except Exception as e:
            logger.debug("YOLO inference failed: %s", e)
            return []

        detections: List[Detection] = []
        for r in results:
            if not hasattr(r, "boxes") or r.boxes is None:
                continue
            for b in r.boxes:
                cls_id = int(b.cls[0]) if len(b.cls) > 0 else 0
                name = self._model.names.get(cls_id, f"class_{cls_id}") if hasattr(self._model, "names") else "target"

                if self.config.yolo_accept_classes and name not in self.config.yolo_accept_classes:
                    continue

                x1, y1, x2, y2 = b.xyxy[0].tolist()
                box_conf = float(b.conf[0]) if len(b.conf) > 0 else conf

                det = DetectionParser.parse_xyxy_box(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    confidence=box_conf,
                    class_name=name,
                    class_id=cls_id,
                    source=DetectionSource.YOLO,
                    frame_id=frame_id,
                    timestamp_sec=timestamp_sec,
                )
                if det is not None:
                    detections.append(det)

        return detections

    def get_info(self) -> Dict[str, Any]:
        return {
            "backend": "yolo",
            "model_path": self.config.yolo_model_path,
            "device": self.config.yolo_device,
            "input_size": self.config.yolo_input_size,
            "confidence_threshold": self.config.yolo_confidence_threshold,
            "accepted_classes": list(self.config.yolo_accept_classes),
            "is_available": self._is_available,
        }
