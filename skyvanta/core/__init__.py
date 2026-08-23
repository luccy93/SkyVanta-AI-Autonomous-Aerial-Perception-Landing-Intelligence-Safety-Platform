"""Core types, configuration, logging, and exceptions for SkyVanta AI."""

from skyvanta.core.types import (
    BoundingBox,
    Detection,
    TrackState,
    TrackInfo,
    TelemetryEstimate,
    ApproachCorridorGeometry,
    FrameMetadata,
    PerceptionResult,
)
from skyvanta.core.config import SkyVantaConfig
from skyvanta.core.logging import get_logger
from skyvanta.core.exceptions import (
    SkyVantaError,
    VideoSourceError,
    ModelLoadError,
    ConfigurationError,
)

__all__ = [
    "BoundingBox",
    "Detection",
    "TrackState",
    "TrackInfo",
    "TelemetryEstimate",
    "ApproachCorridorGeometry",
    "FrameMetadata",
    "PerceptionResult",
    "SkyVantaConfig",
    "get_logger",
    "SkyVantaError",
    "VideoSourceError",
    "ModelLoadError",
    "ConfigurationError",
]
