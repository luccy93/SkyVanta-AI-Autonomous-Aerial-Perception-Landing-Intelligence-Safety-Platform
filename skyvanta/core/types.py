"""Core data types and structures for SkyVanta AI.

All coordinates, estimates, and states are strictly typed with documented units.
Note: Telemetry estimates represent 2D image-space visual heuristics
and are explicitly labeled as estimated/heuristic.
"""

import math
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class TrackState(str, Enum):
    """Discrete state machine states for visual target tracking (legacy compatibility)."""
    SEARCHING = "SEARCHING"
    ACQUIRED = "ACQUIRED"
    TRACKING = "TRACKING"
    LOCKED = "LOCKED"
    APPROACHING = "APPROACHING"


class TrackLifecycleState(str, Enum):
    """Deterministic lifecycle states for multi-target tracking."""
    TENTATIVE = "TENTATIVE"    # Newly initialized track candidate
    CONFIRMED = "CONFIRMED"    # Validated by consecutive detections
    TRACKING = "TRACKING"      # Actively receiving measurements
    COASTING = "COASTING"      # Temporarily missing measurements (Kalman dead-reckoning)
    LOST = "LOST"              # Degraded beyond coasting window
    DELETED = "DELETED"        # Marked for permanent removal


class DetectionSource(str, Enum):
    """Source provenance of a visual detection or target candidate."""
    YOLO = "yolo"
    MOTION = "motion"
    YOLO_MOTION = "yolo+motion"
    OPTICAL_FLOW = "optical_flow"
    MOCK = "mock"


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

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height > 0.0 else 0.0

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)

    def to_int_tuple(self) -> Tuple[int, int, int, int]:
        return (int(round(self.x1)), int(round(self.y1)), int(round(self.x2)), int(round(self.y2)))

    def is_valid(self, min_size: float = 1.0) -> bool:
        """Checks if bounding box coordinates are finite, properly ordered, and meet minimum size."""
        for val in (self.x1, self.y1, self.x2, self.y2):
            if math.isnan(val) or math.isinf(val):
                return False
        return (self.x2 > self.x1) and (self.y2 > self.y1) and (self.width >= min_size) and (self.height >= min_size)

    def clip(self, max_width: float, max_height: float, min_x: float = 0.0, min_y: float = 0.0) -> "BoundingBox":
        """Clips bounding box to frame boundaries safely."""
        cx1 = max(min_x, min(float(max_width), self.x1))
        cy1 = max(min_y, min(float(max_height), self.y1))
        cx2 = max(min_x, min(float(max_width), self.x2))
        cy2 = max(min_y, min(float(max_height), self.y2))
        return BoundingBox(x1=min(cx1, cx2), y1=min(cy1, cy2), x2=max(cx1, cx2), y2=max(cy1, cy2))

    def iou(self, other: "BoundingBox") -> float:
        """Computes Intersection over Union (IoU) with another bounding box."""
        if not self.is_valid() or not other.is_valid():
            return 0.0
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
    """Single semantic object detection."""
    bbox: BoundingBox
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    class_name: str = Field(default="drone", description="Class label")
    class_id: Optional[int] = Field(default=None, description="Integer class identifier")
    source: DetectionSource = Field(default=DetectionSource.YOLO, description="Detection source provenance")
    timestamp_sec: Optional[float] = Field(default=None, description="Timestamp in seconds")
    frame_id: Optional[int] = Field(default=None, description="Frame index")


class MotionCandidate(BaseModel):
    """Motion-segmented foreground candidate."""
    bbox: BoundingBox
    motion_score: float = Field(..., ge=0.0, description="Raw motion and contrast score")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Normalized motion confidence")
    contour_area: float = Field(default=0.0, description="Contour pixel area")
    edge_density: float = Field(default=0.0, description="Canny edge density ratio")
    source: DetectionSource = Field(default=DetectionSource.MOTION)


class OpticalFlowResult(BaseModel):
    """Aggregated optical flow metrics across a video frame or ROI."""
    mean_magnitude: float = Field(default=0.0, description="Mean optical flow magnitude in pixels/frame")
    max_magnitude: float = Field(default=0.0, description="Max optical flow magnitude in pixels/frame")
    motion_direction_deg: float = Field(default=0.0, description="Dominant flow motion direction in degrees")
    has_significant_motion: bool = Field(default=False, description="Flag indicating motion above noise floor")


class Candidate(BaseModel):
    """Fused target candidate combining semantic detection, motion, and flow evidence."""
    bbox: BoundingBox
    candidate_score: float = Field(..., ge=0.0, le=1.0, description="Composite candidate score (0.0 to 1.0)")
    source: DetectionSource = Field(..., description="Fused source provenance: yolo, motion, or yolo+motion")
    detection_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    motion_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    flow_evidence: float = Field(default=0.0, ge=0.0, le=1.0)
    class_name: str = Field(default="target")
    evidence_notes: List[str] = Field(default_factory=list)


class PerceptionTiming(BaseModel):
    """Perception component execution latency breakdown in milliseconds."""
    validation_ms: float = Field(default=0.0)
    detection_ms: float = Field(default=0.0)
    motion_ms: float = Field(default=0.0)
    optical_flow_ms: float = Field(default=0.0)
    fusion_ms: float = Field(default=0.0)
    selection_ms: float = Field(default=0.0)
    total_ms: float = Field(default=0.0)


class TrajectoryPoint(BaseModel):
    """Historical 2D trajectory waypoint in pixel space."""
    x: float = Field(..., description="Center x in image pixels")
    y: float = Field(..., description="Center y in image pixels")
    w: Optional[float] = Field(default=None, description="Bounding box width in pixels")
    h: Optional[float] = Field(default=None, description="Bounding box height in pixels")
    timestamp_sec: float = Field(..., description="Frame timestamp in seconds")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    state: TrackLifecycleState = Field(default=TrackLifecycleState.TRACKING)


class Track(BaseModel):
    """Full state and trajectory model for a single visual target track."""
    track_id: int = Field(..., description="Unique stable track identifier")
    state: TrackLifecycleState = Field(default=TrackLifecycleState.TENTATIVE)
    bbox: BoundingBox = Field(..., description="Current filtered and smoothed bounding box")
    predicted_bbox: Optional[BoundingBox] = Field(default=None, description="Prior Kalman prediction")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Smoothed confidence score")
    track_quality: float = Field(default=0.5, ge=0.0, le=1.0, description="Composite track quality rating")
    age: int = Field(default=1, description="Total elapsed frames since creation")
    hits: int = Field(default=1, description="Total frames successfully matched with detection")
    consecutive_hits: int = Field(default=1, description="Current run of consecutive hits")
    missed_frames: int = Field(default=0, description="Consecutive frames missing measurement")
    velocity_px_per_sec: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="Estimated 2D image-space velocity (vx, vy) in pixels/second"
    )
    source_class: str = Field(default="drone", description="Class label from detector")
    source: DetectionSource = Field(default=DetectionSource.YOLO, description="Primary detection provenance")
    trajectory: List[TrajectoryPoint] = Field(default_factory=list, description="Bounded trajectory trail")
    created_at_sec: float = Field(default=0.0, description="Timestamp of track initialization")
    last_seen_sec: float = Field(default=0.0, description="Timestamp of most recent measurement update")


class TrackingTiming(BaseModel):
    """Tracking execution latency breakdown in milliseconds."""
    prediction_ms: float = Field(default=0.0)
    association_ms: float = Field(default=0.0)
    update_ms: float = Field(default=0.0)
    smoothing_ms: float = Field(default=0.0)
    lifecycle_ms: float = Field(default=0.0)
    total_ms: float = Field(default=0.0)


class TrackingMetrics(BaseModel):
    """Runtime tracking subsystem diagnostic metrics."""
    active_track_count: int = Field(default=0)
    confirmed_track_count: int = Field(default=0)
    lost_track_count: int = Field(default=0)
    average_track_age: float = Field(default=0.0)
    missed_frame_rate: float = Field(default=0.0)
    id_switch_count: int = Field(default=0)


class TrackingResult(BaseModel):
    """Subsystem output containing all tracks, lifecycle updates, and latency metrics."""
    frame_id: int
    timestamp_sec: float
    tracks: List[Track] = Field(default_factory=list, description="All active tracks in any lifecycle state")
    confirmed_tracks: List[Track] = Field(default_factory=list, description="Confirmed tracks (CONFIRMED or TRACKING)")
    lost_tracks: List[Track] = Field(default_factory=list, description="Coasting or lost tracks")
    deleted_track_ids: List[int] = Field(default_factory=list, description="Track IDs removed in this frame")
    timing: TrackingTiming = Field(default_factory=TrackingTiming)
    metrics: TrackingMetrics = Field(default_factory=TrackingMetrics)


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
    """Snapshot of the active target track state (legacy HUD compatibility)."""
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


class PerceptionFrameResult(BaseModel):
    """Comprehensive perception subsystem output for a single frame."""
    frame_id: int
    timestamp_sec: float
    is_valid_frame: bool = True
    detections: List[Detection] = Field(default_factory=list)
    motion_candidates: List[MotionCandidate] = Field(default_factory=list)
    optical_flow: Optional[OpticalFlowResult] = None
    fused_candidates: List[Candidate] = Field(default_factory=list)
    selected_target: Optional[Candidate] = None
    timing: PerceptionTiming = Field(default_factory=PerceptionTiming)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


class CameraIntrinsics(BaseModel):
    """Calibrated pinhole camera intrinsic parameters and lens distortion coefficients."""
    image_width: int = Field(..., gt=0, description="Image frame width in pixels")
    image_height: int = Field(..., gt=0, description="Image frame height in pixels")
    fx: float = Field(..., gt=0.0, description="Focal length along X axis in pixels")
    fy: float = Field(..., gt=0.0, description="Focal length along Y axis in pixels")
    cx: float = Field(..., description="Principal point X coordinate in pixels")
    cy: float = Field(..., description="Principal point Y coordinate in pixels")
    distortion_coefficients: List[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0, 0.0, 0.0],
        description="Distortion coefficients [k1, k2, p1, p2, k3...]"
    )


class LandingTarget(BaseModel):
    """Unified detected visual target or fiducial marker representation in image space."""
    target_id: int = Field(default=0, description="Assigned target identifier")
    marker_family: str = Field(default="aruco", description="Fiducial family (e.g. DICT_6X6_250, tag36h11)")
    marker_id: int = Field(default=0, description="Decoded numerical fiducial ID")
    corners: List[Tuple[float, float]] = Field(
        ...,
        description="4 ordered corner coordinates (u, v) in pixels: [Top-Left, Top-Right, Bottom-Right, Bottom-Left]"
    )
    center: Tuple[float, float] = Field(..., description="Geometric center pixel coordinate (u, v)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Detector confidence score [0.0, 1.0]")
    timestamp_sec: float = Field(default=0.0, description="Frame capture timestamp in seconds")
    frame_id: int = Field(default=0, description="Source video frame index")
    source: str = Field(default="aruco", description="Detection algorithm source provenance")


class Pose6D(BaseModel):
    """6-DoF spatial pose of a target relative to the camera optical frame.

    Units:
        Translation: meters (X: right, Y: down, Z: forward into scene)
        Angles: degrees / radians
    """
    x: float = Field(..., description="Translation along camera X-axis (right positive) in meters")
    y: float = Field(..., description="Translation along camera Y-axis (down positive) in meters")
    z: float = Field(..., description="Translation along camera Z-axis (forward optical depth) in meters")
    rotation_matrix: List[List[float]] = Field(..., description="3x3 orthonormal rotation matrix R_target_to_cam")
    rvec: Tuple[float, float, float] = Field(..., description="Rodrigues rotation vector [rx, ry, rz] in radians")
    quaternion: Tuple[float, float, float, float] = Field(..., description="Unit quaternion [qw, qx, qy, qz]")
    euler_deg: Tuple[float, float, float] = Field(..., description="Euler angles [roll, pitch, yaw] in degrees")
    euler_rad: Tuple[float, float, float] = Field(..., description="Euler angles [roll, pitch, yaw] in radians")
    range_m: float = Field(..., description="Euclidean distance from camera center to target in meters")
    reprojection_error_rms: float = Field(default=0.0, description="RMS reprojection error across all corners in pixels")
    reprojection_error_max: float = Field(default=0.0, description="Maximum single-corner reprojection error in pixels")
    pose_quality: float = Field(default=1.0, ge=0.0, le=1.0, description="Composite pose quality metric [0.0, 1.0]")
    is_valid: bool = Field(default=True, description="Whether the pose passed all geometric sanity checks")
    timestamp_sec: float = Field(default=0.0, description="Timestamp of pose estimation")
    frame_id: int = Field(default=0, description="Video frame index")
    target_id: int = Field(default=0, description="Associated target identifier")
    solver_method: str = Field(default="IPPE", description="OpenCV PnP solver algorithm used")


class PoseEstimateResult(BaseModel):
    """Complete output of the 6-DoF PnP spatial pose estimation pipeline for a frame."""
    timestamp_sec: float
    frame_id: int
    target_id: Optional[int] = None
    pose: Optional[Pose6D] = None
    target: Optional[LandingTarget] = None
    reprojection_error_rms: Optional[float] = None
    pose_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    is_valid: bool = Field(default=False)
    failure_reason: Optional[str] = None
    solver_metadata: Dict[str, Any] = Field(default_factory=dict)


class LandingPad(BaseModel):
    """Unified landing pad abstraction supporting multi-stage detection modalities."""
    pad_id: int = Field(default=1, description="Unique landing pad identifier")
    target_type: str = Field(default="fiducial", description="Target type: fiducial, contour, or deep")
    marker_id: Optional[int] = Field(default=None, description="Decoded marker ID if fiducial")
    marker_size_m: float = Field(default=0.20, gt=0.0, description="Physical side length of the square pad in meters")
    pose: Optional[Pose6D] = Field(default=None, description="Estimated camera-relative 6-DoF pose")
    corners_2d: List[Tuple[float, float]] = Field(default_factory=list, description="Observed 2D corner pixels")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Detection confidence score")
    is_trackable: bool = Field(default=True, description="Whether the pad is currently trackable")


class FrameId(str, Enum):
    """Strongly-typed coordinate frame identifiers across the platform."""
    CAMERA = "CAMERA"            # Standard pinhole optical frame (+X: right, +Y: down, +Z: forward)
    BODY = "BODY"                # Drone body frame (+X: forward, +Y: right, +Z: down - NED)
    WORLD = "WORLD"              # Global / local navigation inertial frame
    LANDING_PAD = "LANDING_PAD"  # Planar target frame (+X: right, +Y: down, +Z: normal into surface)
    CUSTOM = "CUSTOM"            # User-defined custom auxiliary frame


class TransformStatus(str, Enum):
    """Availability and dynamics classification of a spatial coordinate transform."""
    STATIC = "STATIC"            # Time-invariant extrinsic transformation (e.g. mounting)
    DYNAMIC = "DYNAMIC"          # Time-varying state transform (e.g. visual odometry / tracking)
    UNAVAILABLE = "UNAVAILABLE"  # Frame relationship is known conceptually but no measurement exists


class SpatialUncertainty(BaseModel):
    """Spatial uncertainty and covariance representation contract for future sensor fusion."""
    is_available: bool = Field(default=False, description="Whether covariance estimates are populated")
    translation_std_m: Optional[Tuple[float, float, float]] = Field(
        default=None, description="Standard deviations (sigma_x, sigma_y, sigma_z) in meters"
    )
    rotation_std_rad: Optional[Tuple[float, float, float]] = Field(
        default=None, description="Angular standard deviations (sigma_roll, sigma_pitch, sigma_yaw) in radians"
    )
    covariance_matrix: Optional[List[List[float]]] = Field(
        default=None, description="6x6 spatial covariance matrix [pos(3), rot(3)] if available"
    )


class SpatialLocalizationResult(BaseModel):
    """Unified result of transforming a target pose across coordinate frames."""
    target_id: Optional[int] = Field(default=None, description="Associated target identifier")
    source_frame: FrameId = Field(..., description="Original coordinate frame of the measurement")
    target_frame: FrameId = Field(..., description="Target coordinate frame of the expressed pose")
    pose: Optional[Pose6D] = Field(default=None, description="Transformed 6-DoF pose in target frame")
    homogeneous_matrix: Optional[List[List[float]]] = Field(
        default=None, description="4x4 homogeneous transformation matrix T_target_source"
    )
    timestamp_sec: float = Field(default=0.0, description="Measurement capture timestamp")
    transform_chain: List[str] = Field(
        default_factory=list, description="Sequence of frame hops traversed (e.g. ['LANDING_PAD', 'CAMERA', 'BODY'])"
    )
    is_valid: bool = Field(default=False, description="Whether the transformation chain was valid and successfully computed")
    is_world_relative: bool = Field(
        default=False, description="Explicit flag: True ONLY if expressed relative to a valid WORLD reference"
    )
    failure_reason: Optional[str] = Field(default=None, description="Diagnostic reason if transform failed or was unavailable")
    uncertainty: SpatialUncertainty = Field(default_factory=SpatialUncertainty)
    quality_metadata: Dict[str, Any] = Field(default_factory=dict)


class PerceptionResult(BaseModel):
    """Complete perception and estimation output for a single frame (V1 pipeline compatibility)."""
    metadata: FrameMetadata
    track: Optional[TrackInfo] = None
    telemetry: Optional[TelemetryEstimate] = None
    corridor: Optional[ApproachCorridorGeometry] = None
    perception_frame: Optional[PerceptionFrameResult] = None
    tracking_result: Optional[TrackingResult] = None
    pose_result: Optional[PoseEstimateResult] = None
    spatial_localization: Optional[SpatialLocalizationResult] = None


