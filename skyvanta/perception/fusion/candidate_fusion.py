"""Candidate fusion engine associating semantic detections, motion candidates, and optical flow."""

from typing import List, Optional, Tuple
from skyvanta.core.config import FusionConfig
from skyvanta.core.types import BoundingBox, Candidate, Detection, DetectionSource, MotionCandidate
from skyvanta.perception.fusion.scoring import CandidateScorer


class CandidateFusionEngine:
    """Combines and cross-associates multi-cue detection candidates."""

    def __init__(self, config: Optional[FusionConfig] = None):
        self.config = config or FusionConfig()
        self.scorer = CandidateScorer(self.config)

    def fuse(
        self,
        detections: List[Detection],
        motion_candidates: List[MotionCandidate],
        flow_energy_fn: Optional[any] = None,
    ) -> List[Candidate]:
        """Cross-correlates semantic detections and motion candidates.

        Returns:
            List of ranked `Candidate` objects with clear source provenance.
        """
        candidates: List[Candidate] = []
        matched_motion_indices = set()

        # Step 1: Match YOLO detections with overlapping Motion candidates
        for det in detections:
            best_iou = 0.0
            best_m_idx = -1

            for m_idx, mot in enumerate(motion_candidates):
                iou = det.bbox.iou(mot.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_m_idx = m_idx

            if best_m_idx >= 0 and best_iou >= self.config.iou_threshold:
                matched_motion_indices.add(best_m_idx)
                mot = motion_candidates[best_m_idx]

                # Blend bounding boxes weighted by confidence
                w_y = det.confidence / (det.confidence + mot.confidence + 1e-6)
                w_m = 1.0 - w_y
                fused_bbox = BoundingBox(
                    x1=det.bbox.x1 * w_y + mot.bbox.x1 * w_m,
                    y1=det.bbox.y1 * w_y + mot.bbox.y1 * w_m,
                    x2=det.bbox.x2 * w_y + mot.bbox.x2 * w_m,
                    y2=det.bbox.y2 * w_y + mot.bbox.y2 * w_m,
                )

                flow_val = flow_energy_fn(fused_bbox) if flow_energy_fn else 0.5
                score = self.scorer.score(
                    det_conf=det.confidence,
                    mot_conf=mot.confidence,
                    flow_conf=flow_val,
                    iou=best_iou,
                )

                candidates.append(Candidate(
                    bbox=fused_bbox,
                    candidate_score=score,
                    source=DetectionSource.YOLO_MOTION,
                    detection_confidence=det.confidence,
                    motion_confidence=mot.confidence,
                    flow_evidence=flow_val,
                    class_name=det.class_name,
                    evidence_notes=[
                        f"YOLO conf={det.confidence:.2f}",
                        f"Motion score={mot.motion_score:.1f}",
                        f"Overlap IoU={best_iou:.2f}",
                    ],
                ))
            else:
                # Isolated YOLO detection
                flow_val = flow_energy_fn(det.bbox) if flow_energy_fn else 0.0
                score = self.scorer.score(
                    det_conf=det.confidence,
                    mot_conf=0.0,
                    flow_conf=flow_val,
                    iou=0.0,
                )

                candidates.append(Candidate(
                    bbox=det.bbox,
                    candidate_score=score,
                    source=DetectionSource.YOLO,
                    detection_confidence=det.confidence,
                    motion_confidence=0.0,
                    flow_evidence=flow_val,
                    class_name=det.class_name,
                    evidence_notes=[f"YOLO isolated conf={det.confidence:.2f}"],
                ))

        # Step 2: Add unmatched motion candidates
        for m_idx, mot in enumerate(motion_candidates):
            if m_idx in matched_motion_indices:
                continue

            flow_val = flow_energy_fn(mot.bbox) if flow_energy_fn else 0.4
            score = self.scorer.score(
                det_conf=0.0,
                mot_conf=mot.confidence,
                flow_conf=flow_val,
                iou=0.0,
            )

            candidates.append(Candidate(
                bbox=mot.bbox,
                candidate_score=score,
                source=DetectionSource.MOTION,
                detection_confidence=0.0,
                motion_confidence=mot.confidence,
                flow_evidence=flow_val,
                class_name="motion_target",
                evidence_notes=[f"Motion contrast score={mot.motion_score:.1f}"],
            ))

        # Sort candidates by composite candidate_score descending
        candidates.sort(key=lambda c: c.candidate_score, reverse=True)
        return candidates

    def pick_best(
        self,
        yolo_detections: List[Detection],
        motion_detections: List[any],
    ) -> Tuple[Optional[BoundingBox], float]:
        """V1 backward-compatibility method."""
        if not yolo_detections and not motion_detections:
            return None, 0.0

        if yolo_detections and motion_detections:
            best_y = max(yolo_detections, key=lambda d: d.confidence)
            first_m = motion_detections[0]
            m_box = first_m.bbox if hasattr(first_m, "bbox") else BoundingBox(x1=first_m[0], y1=first_m[1], x2=first_m[2], y2=first_m[3])

            iou = best_y.bbox.iou(m_box)
            if iou > self.config.iou_threshold:
                fused_box = BoundingBox(
                    x1=(best_y.bbox.x1 + m_box.x1) / 2.0,
                    y1=(best_y.bbox.y1 + m_box.y1) / 2.0,
                    x2=(best_y.bbox.x2 + m_box.x2) / 2.0,
                    y2=(best_y.bbox.y2 + m_box.y2) / 2.0,
                )
                return fused_box, 0.90
            else:
                return m_box, 0.65

        if motion_detections:
            first_m = motion_detections[0]
            m_box = first_m.bbox if hasattr(first_m, "bbox") else BoundingBox(x1=first_m[0], y1=first_m[1], x2=first_m[2], y2=first_m[3])
            return m_box, 0.55

        best_y = max(yolo_detections, key=lambda d: d.confidence)
        return best_y.bbox, 0.50


# Alias for backward compatibility
CandidateFusion = CandidateFusionEngine
