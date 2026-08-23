"""Core data types and structures for SkyVanta AI.

All coordinates, estimates, and states are strictly typed with documented units.
Note: Telemetry estimates in V1 represent 2D image-space visual heuristics
and are explicitly labeled as estimated/heuristic.
"""

from enum import Enum
from typing import List, Optional, Tuple, Deque
from pydantic import BaseModel, Field


class TrackState(str, Enum):
    """Discrete state machine states for visual target tracking."""
    SEARCHING = "SEARCHING"
    ACQUIRED = "ACQUIRED"
    TRACKING = "TRACKING"
    LOCKED = "LOCKED"
    APPROACHING = "APPROACHING"


class BoundingBox(BaseModel):
    """2D rectangular bounding box in image pixel coordinates."""
    x1: float = Field(..., description="Top-left x pixel coordinate")
    y1: float = Field(..., description="Top-left y pixel coordinate")
    x2: float = Field(..., description="Bottom-right x pixel coordinate")
    y2: float = Field(..., description="Bottom-right y pixel coordinate")

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)

    def iou(self, other: "BoundingBox") -> float:
        """Computes Intersection over Union (IoU) with another bounding box."""
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        intersection = iw * ih
        union = self.area + other.area - intersection
        return intersection / union if union > 0.0 else 0.0


class Detection(BaseModel):
    """Single object detection candidate."""
    bbox: BoundingBox
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    class_name: str = Field(default="drone", description="Class label")
    source: str = Field(default="yolo", description="Detection source: yolo or motion")


class TelemetryEstimate(BaseModel):
    """Heuristic visual telemetry estimations derived from 2D bounding box scaling.

    IMPORTANT: These are visual approximations for HUD telemetry display,
    not certified physical measurements.
    """
    estimated_distance_m: float = Field(..., description="Estimated distance in meters (heuristic)")
    estimated_altitude_m: float = Field(..., description="Estimated altitude in meters (heuristic)")
    estimated_approach_angle_deg: float = Field(..., description="Estimated approach angle in degrees")
    estimated_alignment_pct: float = Field(..., ge=0.0, le=100.0, description="Alignment percentage")
    estimated_lateral_offset_m: float = Field(..., description="Estimated lateral offset in meters")
    estimated_vertical_offset_m: float = Field(..., description="Estimated vertical offset in meters")
    landing_confidence_pct: float = Field(..., ge=0.0, le=100.0, description="Composite landing confidence %")


class ApproachCorridorGeometry(BaseModel):
    """2D perspective approach corridor geometry points."""
    apex: Tuple[float, float]
    tl: Tuple[float, float]
    tr: Tuple[float, float]
    bl: Tuple[float, float]
    br: Tuple[float, float]
    center: Tuple[float, float]
    closeness: float = Field(..., ge=0.0, le=1.0)


class FrameMetadata(BaseModel):
    """Metadata for a processed video frame."""
    frame_index: int
    timestamp_sec: float
    source_width: int
    source_height: int
    processed_width: int
    processed_height: int
    fps: float


class TrackInfo(BaseModel):
    """Snapshot of the active target track state."""
    track_id: int
    state: TrackState
    confidence: float = Field(..., ge=0.0, le=1.0)
    hits: int
    frames_since_hit: int
    age: int
    is_visible: bool
    bbox: Optional[BoundingBox] = None
    center: Optional[Tuple[float, float]] = None
    size: Optional[Tuple[float, float]] = None


class PerceptionResult(BaseModel):
    """Complete perception and estimation output for a single frame."""
    metadata: FrameMetadata
    track: Optional[TrackInfo] = None
    telemetry: Optional[TelemetryEstimate] = None
    corridor: Optional[ApproachCorridorGeometry] = None
