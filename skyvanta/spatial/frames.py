"""Coordinate frame definitions, metadata, and standardization."""

from typing import Dict, Optional
from pydantic import BaseModel, Field
from skyvanta.core.types import FrameId


class FrameDefinition(BaseModel):
    """Formal metadata definition and spatial conventions for a coordinate frame."""
    frame_id: FrameId = Field(..., description="Unique strongly-typed frame identifier")
    parent_frame: Optional[FrameId] = Field(default=None, description="Default hierarchical parent frame")
    convention: str = Field(default="RIGHT_HANDED", description="Coordinate axis convention (e.g. RIGHT_HANDED, NED, ENU)")
    axes_description: str = Field(default="", description="Human-readable description of +X, +Y, +Z axes")
    units: str = Field(default="meters", description="Metric unit for linear coordinates")
    is_inertial: bool = Field(default=False, description="Whether this coordinate frame represents an inertial world reference")


# Standard Platform Frame Registry
STANDARD_FRAMES: Dict[FrameId, FrameDefinition] = {
    FrameId.CAMERA: FrameDefinition(
        frame_id=FrameId.CAMERA,
        parent_frame=FrameId.BODY,
        convention="RIGHT_HANDED",
        axes_description="+X: right along sensor scanlines, +Y: down along sensor columns, +Z: forward optical axis",
        units="meters",
        is_inertial=False,
    ),
    FrameId.BODY: FrameDefinition(
        frame_id=FrameId.BODY,
        parent_frame=FrameId.WORLD,
        convention="NED",
        axes_description="+X: forward along aircraft nose, +Y: right along aircraft starboard wing, +Z: down toward ground",
        units="meters",
        is_inertial=False,
    ),
    FrameId.LANDING_PAD: FrameDefinition(
        frame_id=FrameId.LANDING_PAD,
        parent_frame=FrameId.CAMERA,
        convention="RIGHT_HANDED",
        axes_description="+X: right along marker plane, +Y: down along marker plane, +Z: normal pointing into pad surface",
        units="meters",
        is_inertial=False,
    ),
    FrameId.WORLD: FrameDefinition(
        frame_id=FrameId.WORLD,
        parent_frame=None,
        convention="NED",
        axes_description="+X: North, +Y: East, +Z: Down (Inertial Navigation Reference)",
        units="meters",
        is_inertial=True,
    ),
}
