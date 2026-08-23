"""Video frame validation and sanity checking."""

import math
from typing import Optional, Tuple
import numpy as np


class FrameValidator:
    """Validates raw image frames for processing safety."""

    @staticmethod
    def validate(
        frame: Optional[np.ndarray],
        min_width: int = 16,
        min_height: int = 16,
    ) -> Tuple[bool, Optional[str]]:
        """Checks if a frame is valid, non-empty, and has supported dimensions/channels.

        Returns:
            (is_valid, error_message): (True, None) if valid, (False, reason) if malformed.
        """
        if frame is None:
            return False, "Frame is None"

        if not isinstance(frame, np.ndarray):
            return False, f"Frame must be a numpy.ndarray, got {type(frame).__name__}"

        if frame.dtype != np.uint8:
            return False, f"Frame must have dtype uint8, got {frame.dtype}"

        if frame.size == 0:
            return False, "Frame is empty (size == 0)"

        shape = frame.shape
        if len(shape) not in (2, 3):
            return False, f"Expected 2D or 3D image array, got shape {shape}"

        h, w = shape[:2]
        if h < min_height or w < min_width:
            return False, f"Frame dimensions {w}x{h} below minimum threshold {min_width}x{min_height}"

        if len(shape) == 3 and shape[2] not in (1, 3, 4):
            return False, f"Unsupported channel count {shape[2]} (expected 1, 3, or 4)"

        return True, None
