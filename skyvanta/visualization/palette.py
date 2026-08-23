"""Color palette definitions for HUD overlays (BGR format for OpenCV)."""

from typing import Tuple

Color = Tuple[int, int, int]


class Palette:
    """Standardized HUD color scheme in OpenCV BGR format."""
    CYAN: Color = (255, 240, 60)
    CYAN_SOFT: Color = (230, 200, 90)
    TEAL: Color = (200, 180, 40)
    GREEN: Color = (140, 235, 120)
    GREEN_DIM: Color = (90, 160, 80)
    WHITE: Color = (245, 245, 245)
    WHITE_DIM: Color = (190, 190, 190)
    RED_WARN: Color = (80, 80, 235)
    AMBER: Color = (60, 170, 235)
    BG_PANEL: Color = (28, 22, 18)
    GRID: Color = (90, 70, 50)
