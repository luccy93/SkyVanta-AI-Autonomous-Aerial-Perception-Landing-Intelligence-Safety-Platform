"""Centralized configuration models for SkyVanta AI.

Eliminates scattered magic numbers and provides clean YAML/dictionary loading.
"""

from typing import Optional, Set
from pydantic import BaseModel, Field
import yaml
import os


class DetectorConfig(BaseModel):
    """Configuration for YOLO and Motion detectors."""
    use_yolo: bool = Field(default=True, description="Enable YOLO deep learning detector")
    yolo_model_path: str = Field(default="yolov8n.pt", description="Path or name of YOLO weights")
    yolo_confidence_threshold: float = Field(default=0.08, ge=0.01, le=1.0)
    yolo_input_size: int = Field(default=640, description="Inference image dimension")
    yolo_accept_classes: Set[str] = Field(
        default={"airplane", "bird", "kite", "frisbee"},
        description="Target class labels accepted by proxy detector"
    )
    motion_history: int = Field(default=120, description="MOG2 background history frames")
    motion_var_threshold: float = Field(default=18.0, description="MOG2 variance threshold")
    motion_min_area_ratio: float = Field(default=0.00004, description="Min contour area ratio")
    motion_max_area_ratio: float = Field(default=0.06, description="Max contour area ratio")
    fusion_iou_threshold: float = Field(default=0.1, description="IoU threshold to fuse YOLO + Motion")


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
    """Configuration for target tracking state machine and Kalman filter."""
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


class PipelineConfig(BaseModel):
    """Configuration for end-to-end video pipeline."""
    max_dimension: int = Field(default=1280, description="Max width or height for processing")
    default_fps: float = Field(default=30.0, description="Fallback FPS if unreadable from video")
    output_dir: str = Field(default="output", description="Directory to save rendered videos")
    demo_duration_sec: float = Field(default=13.0, description="Demo mode duration in seconds")


class SkyVantaConfig(BaseModel):
    """Master configuration structure for SkyVanta AI."""
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    smoothing: SmoothingConfig = Field(default_factory=SmoothingConfig)
    tracker: TrackerConfig = Field(default_factory=TrackerConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)

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
