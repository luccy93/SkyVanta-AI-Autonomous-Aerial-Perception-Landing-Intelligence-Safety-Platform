"""Centralized configuration models for SkyVanta AI.

Eliminates scattered magic numbers and provides clean YAML/dictionary loading.
"""

from typing import List, Optional, Set
from pydantic import BaseModel, Field
import yaml
import os


class DetectorConfig(BaseModel):
    """Configuration for deep learning object detectors."""
    use_yolo: bool = Field(default=True, description="Enable YOLO deep learning detector")
    yolo_model_path: str = Field(default="yolov8n.pt", description="Path or name of YOLO weights")
    yolo_confidence_threshold: float = Field(default=0.08, ge=0.01, le=1.0)
    yolo_iou_threshold: float = Field(default=0.45, ge=0.01, le=1.0)
    yolo_input_size: int = Field(default=640, description="Inference image dimension")
    yolo_device: str = Field(default="cpu", description="Inference device: cpu, cuda:0, etc.")
    yolo_accept_classes: Set[str] = Field(
        default={"airplane", "bird", "kite", "frisbee"},
        description="Target class labels accepted by proxy detector"
    )
    motion_history: int = Field(default=120, description="MOG2 background history frames (legacy alias)")
    motion_var_threshold: float = Field(default=18.0, description="MOG2 variance threshold (legacy alias)")
    motion_min_area_ratio: float = Field(default=0.00004, description="Min contour area ratio (legacy alias)")
    motion_max_area_ratio: float = Field(default=0.06, description="Max contour area ratio (legacy alias)")
    fusion_iou_threshold: float = Field(default=0.1, description="IoU threshold to fuse YOLO + Motion (legacy alias)")


class MotionConfig(BaseModel):
    """Configuration for background subtraction and contour motion analysis."""
    enabled: bool = Field(default=True, description="Enable motion contrast detection")
    history: int = Field(default=120, description="MOG2 history frame count")
    var_threshold: float = Field(default=18.0, description="MOG2 variance threshold")
    detect_shadows: bool = Field(default=False, description="MOG2 shadow detection flag")
    min_area_ratio: float = Field(default=0.00004, description="Minimum contour area ratio of frame")
    max_area_ratio: float = Field(default=0.06, description="Maximum contour area ratio of frame")
    min_aspect_ratio: float = Field(default=0.25, description="Minimum width/height aspect ratio")
    max_aspect_ratio: float = Field(default=4.5, description="Maximum width/height aspect ratio")
    edge_weight: float = Field(default=3.0, description="Multiplier for Canny edge density scoring")


class OpticalFlowConfig(BaseModel):
    """Configuration for dense Farneback optical flow."""
    enabled: bool = Field(default=True, description="Enable dense optical flow calculation")
    pyr_scale: float = Field(default=0.5, description="Image scale (<1) to build pyramids")
    levels: int = Field(default=2, description="Number of pyramid layers")
    winsize: int = Field(default=15, description="Averaging window size")
    iterations: int = Field(default=2, description="Iterations at each pyramid level")
    poly_n: int = Field(default=5, description="Pixel neighborhood polynomial expansion size")
    poly_sigma: float = Field(default=1.1, description="Gaussian standard deviation for polynomial derivative")
    magnitude_threshold: float = Field(default=40.0, description="Normalized magnitude threshold for flow mask")


class FusionConfig(BaseModel):
    """Configuration for candidate fusion and scoring."""
    iou_threshold: float = Field(default=0.10, description="Spatial IoU threshold to associate detections and motion")
    weight_detection: float = Field(default=0.50, description="Weight for semantic detector confidence in candidate_score")
    weight_motion: float = Field(default=0.30, description="Weight for motion contrast confidence in candidate_score")
    weight_flow: float = Field(default=0.10, description="Weight for optical flow energy in candidate_score")
    weight_iou: float = Field(default=0.10, description="Weight for detector/motion overlap in candidate_score")


class TargetSelectionConfig(BaseModel):
    """Configuration for target selection heuristics."""
    min_candidate_score: float = Field(default=0.15, description="Minimum candidate score to qualify as target")
    min_box_area_ratio: float = Field(default=0.00004, description="Minimum bounding box area relative to image")
    max_box_area_ratio: float = Field(default=0.25, description="Maximum bounding box area relative to image")
    roi_top_cutoff_ratio: float = Field(default=0.85, description="Ignore candidates below this vertical ratio")


class PerceptionConfig(BaseModel):
    """Master configuration for the Computer Vision Perception Subsystem."""
    enabled: bool = Field(default=True, description="Enable perception subsystem")
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    motion: MotionConfig = Field(default_factory=MotionConfig)
    optical_flow: OpticalFlowConfig = Field(default_factory=OpticalFlowConfig)
    fusion: FusionConfig = Field(default_factory=FusionConfig)
    selection: TargetSelectionConfig = Field(default_factory=TargetSelectionConfig)


class AssociationConfig(BaseModel):
    """Configuration for data association and spatial gating."""
    min_iou: float = Field(default=0.15, ge=0.0, le=1.0, description="Minimum IoU to accept association match")
    max_center_distance_px: float = Field(default=180.0, description="Maximum center pixel displacement gate")
    min_scale_ratio: float = Field(default=0.2, description="Minimum area ratio between detection and track")
    max_scale_ratio: float = Field(default=5.0, description="Maximum area ratio between detection and track")


class LifecycleConfig(BaseModel):
    """Configuration for track confirmation and deletion state machine."""
    min_confirmed_hits: int = Field(default=3, ge=1, description="Hits needed to transition TENTATIVE -> CONFIRMED")
    max_tentative_misses: int = Field(default=2, ge=1, description="Misses before TENTATIVE track is deleted")
    max_coasting_frames: int = Field(default=15, ge=1, description="Missed frames in COASTING before transition to LOST")
    max_lost_frames: int = Field(default=45, ge=1, description="Missed frames in LOST before permanent DELETION")


class TrajectoryConfig(BaseModel):
    """Configuration for trajectory memory and velocity estimation."""
    max_history_length: int = Field(default=60, ge=5, description="Maximum waypoints stored per track")
    velocity_smoothing_alpha: float = Field(default=0.3, ge=0.0, le=1.0, description="EMA alpha for velocity filter")


class TrackQualityConfig(BaseModel):
    """Configuration for track quality assessment."""
    weight_hit_ratio: float = Field(default=0.40, description="Weight for hit/age ratio")
    weight_confidence: float = Field(default=0.40, description="Weight for smoothed detection confidence")
    weight_continuity: float = Field(default=0.20, description="Weight for consecutive hit continuity")


class TrackingConfig(BaseModel):
    """Comprehensive configuration for Multi-Target Tracking Subsystem."""
    enabled: bool = Field(default=True, description="Enable tracking subsystem")
    association: AssociationConfig = Field(default_factory=AssociationConfig)
    lifecycle: LifecycleConfig = Field(default_factory=LifecycleConfig)
    trajectory: TrajectoryConfig = Field(default_factory=TrajectoryConfig)
    quality: TrackQualityConfig = Field(default_factory=TrackQualityConfig)
    kalman_process_noise: float = Field(default=1e-2, description="Kalman process noise covariance")
    kalman_measurement_noise: float = Field(default=1e-1, description="Kalman measurement noise covariance")


class SmoothingConfig(BaseModel):
    """Configuration for OneEuro adaptive low-pass filters."""
    center_min_cutoff: float = Field(default=1.0, description="Center position min cutoff frequency")
    center_beta: float = Field(default=0.015, description="Center position speed coefficient")
    size_min_cutoff: float = Field(default=1.0, description="Size min cutoff frequency")
    size_beta: float = Field(default=0.01, description="Size speed coefficient")
    telemetry_min_cutoff: float = Field(default=0.8, description="Telemetry filter min cutoff")
    telemetry_beta: float = Field(default=0.01, description="Telemetry filter beta")
    corridor_min_cutoff: float = Field(default=0.7, description="Corridor mesh min cutoff")
    corridor_beta: float = Field(default=0.02, description="Corridor mesh beta")


class TrackerConfig(BaseModel):
    """Legacy configuration for target tracking state machine and Kalman filter."""
    kalman_process_noise: float = Field(default=1e-2, description="Kalman process noise covariance")
    kalman_measurement_noise: float = Field(default=1e-1, description="Kalman measurement noise covariance")
    max_lost_frames: int = Field(default=45, description="Max missed frames before track is dropped")
    jump_distance_ratio: float = Field(default=0.045, description="Max jump distance ratio before trail reset")
    max_trail_length: int = Field(default=45, description="Maximum trail buffer length")
    scale_history_length: int = Field(default=60, description="Scale history length for trend analysis")


class VisualizationConfig(BaseModel):
    """Configuration for HUD overlays and rendering."""
    enabled: bool = Field(default=True, description="Enable visual HUD compositing")
    frame_margin: int = Field(default=24, description="Border margin in pixels")
    fps_target: float = Field(default=30.0, description="Target display framerate")
    show_radar: bool = Field(default=True, description="Render approach radar panel")
    show_corridor: bool = Field(default=True, description="Render 3D perspective approach corridor")
    show_telemetry: bool = Field(default=True, description="Render telemetry readouts")


class CameraConfig(BaseModel):
    """Camera intrinsic parameters and lens distortion model."""
    image_width: int = Field(default=1280, gt=0, description="Image frame width in pixels")
    image_height: int = Field(default=720, gt=0, description="Image frame height in pixels")
    fx: float = Field(default=1000.0, gt=0.0, description="Focal length along X axis in pixels")
    fy: float = Field(default=1000.0, gt=0.0, description="Focal length along Y axis in pixels")
    cx: float = Field(default=640.0, description="Principal point X coordinate in pixels")
    cy: float = Field(default=360.0, description="Principal point Y coordinate in pixels")
    distortion_coefficients: List[float] = Field(
        default_factory=lambda: [0.0, 0.0, 0.0, 0.0, 0.0],
        description="Distortion coefficients [k1, k2, p1, p2, k3...]"
    )


class AprilTagConfig(BaseModel):
    """Configuration for AprilTag fiducial detector."""
    family: str = Field(default="tag36h11", description="AprilTag dictionary family (e.g. tag36h11, tag25h9)")
    tag_size_m: float = Field(default=0.20, gt=0.0, description="Physical marker side length in meters")
    threads: int = Field(default=2, ge=1, description="Number of CPU threads for decoding")
    quad_decimate: float = Field(default=1.0, ge=1.0, description="Decimation factor for quad detection")


class ArucoConfig(BaseModel):
    """Configuration for OpenCV ArUco fiducial detector."""
    dictionary: str = Field(default="DICT_6X6_250", description="ArUco predefined dictionary name")
    marker_size_m: float = Field(default=0.20, gt=0.0, description="Physical marker side length in meters")
    adaptive_thresh_win_size_min: int = Field(default=3, ge=3)
    adaptive_thresh_win_size_max: int = Field(default=23, ge=3)
    adaptive_thresh_win_size_step: int = Field(default=10, ge=1)


class PnPConfig(BaseModel):
    """Configuration for Perspective-n-Point 6-DoF pose solver."""
    solver: str = Field(default="IPPE", description="PnP solver method: IPPE, ITERATIVE, or RANSAC")
    max_reprojection_error_px: float = Field(default=5.0, gt=0.0, description="Maximum allowable RMS reprojection error")
    min_depth_m: float = Field(default=0.05, gt=0.0, description="Minimum valid target distance in meters")
    max_depth_m: float = Field(default=50.0, gt=0.0, description="Maximum valid target distance in meters")


class PoseQualityConfig(BaseModel):
    """Configuration for pose estimation quality rating."""
    max_reproj_error_for_zero_quality: float = Field(default=8.0, gt=0.0)
    min_corner_area_px: float = Field(default=100.0, gt=0.0)


class LandingTargetConfig(BaseModel):
    """Master configuration for the Landing Target and Spatial Pose Subsystem."""
    enabled: bool = Field(default=True, description="Enable spatial target and pose estimation")
    detector_type: str = Field(default="aruco", description="Fiducial detector engine: aruco, apriltag, or mock")
    camera: CameraConfig = Field(default_factory=CameraConfig)
    april_tag: AprilTagConfig = Field(default_factory=AprilTagConfig)
    aruco: ArucoConfig = Field(default_factory=ArucoConfig)
    pnp: PnPConfig = Field(default_factory=PnPConfig)
    quality: PoseQualityConfig = Field(default_factory=PoseQualityConfig)


class PipelineConfig(BaseModel):
    """Configuration for end-to-end video pipeline."""
    max_dimension: int = Field(default=1280, description="Max width or height for processing")
    default_fps: float = Field(default=30.0, description="Fallback FPS if unreadable from video")
    output_dir: str = Field(default="output", description="Directory to save rendered videos")
    demo_duration_sec: float = Field(default=13.0, description="Demo mode duration in seconds")


class SkyVantaConfig(BaseModel):
    """Master configuration structure for SkyVanta AI."""
    perception: PerceptionConfig = Field(default_factory=PerceptionConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    landing_target: LandingTargetConfig = Field(default_factory=LandingTargetConfig)
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    smoothing: SmoothingConfig = Field(default_factory=SmoothingConfig)
    tracker: TrackerConfig = Field(default_factory=TrackerConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)


    def model_post_init(self, __context) -> None:
        """Syncs top-level detector and tracker settings."""
        if self.detector != self.perception.detector:
            self.perception.detector = self.detector

    @classmethod
    def from_yaml(cls, path: str) -> "SkyVantaConfig":
        """Loads configuration from a YAML file."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    def to_yaml(self, path: str) -> None:
        """Saves current configuration to a YAML file."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.model_dump(), f, default_flow_style=False)
