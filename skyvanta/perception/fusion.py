"""Detection candidate fusion and association for SkyVanta AI."""

from typing import List, Optional, Tuple
from skyvanta.core.types import Detection, BoundingBox
from skyvanta.core.config import DetectorConfig


class CandidateFusion:
    """Combines and prioritizes candidate detections from YOLO and motion detectors."""

    def __init__(self, config: Optional[DetectorConfig] = None):
        self.config = config or DetectorConfig()

    def pick_best(
        self,
        yolo_detections: List[Detection],
        motion_detections: List[Detection],
    ) -> Tuple[Optional[BoundingBox], float]:
        """Fuses detection candidates and returns the prioritized bounding box and confidence."""
        if not yolo_detections and not motion_detections:
            return None, 0.0

        if yolo_detections and motion_detections:
            best_yolo = max(yolo_detections, key=lambda d: d.confidence)
            best_motion = motion_detections[0]

            iou = best_yolo.bbox.iou(best_motion.bbox)
            if iou > self.config.fusion_iou_threshold:
                # Average overlapping bounding boxes
                fused_bbox = BoundingBox(
                    x1=(best_yolo.bbox.x1 + best_motion.bbox.x1) / 2.0,
                    y1=(best_yolo.bbox.y1 + best_motion.bbox.y1) / 2.0,
                    x2=(best_yolo.bbox.x2 + best_motion.bbox.x2) / 2.0,
                    y2=(best_yolo.bbox.y2 + best_motion.bbox.y2) / 2.0,
                )
                return fused_bbox, 0.90
            else:
                return best_motion.bbox, 0.65

        if motion_detections:
            return motion_detections[0].bbox, 0.55

        best_yolo = max(yolo_detections, key=lambda d: d.confidence)
        return best_yolo.bbox, 0.50
