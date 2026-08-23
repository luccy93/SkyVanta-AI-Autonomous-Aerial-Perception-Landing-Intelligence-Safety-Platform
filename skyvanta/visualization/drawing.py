"""Anti-aliased drawing utilities for HUD graphics and synthetic overlays."""

import math
from typing import Tuple
import cv2
import numpy as np
from skyvanta.visualization.palette import Palette, Color


def draw_dashed_line(
    img: np.ndarray,
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    color: Color,
    thickness: int = 2,
    dash_len: float = 10.0,
    gap_len: float = 8.0,
    phase: float = 0.0,
) -> None:
    """Renders an anti-aliased dashed line between two points with animated phase shift."""
    np1 = np.array(p1, dtype=float)
    np2 = np.array(p2, dtype=float)
    dist = float(np.linalg.norm(np2 - np1))
    if dist < 1.0:
        return
    direction = (np2 - np1) / dist
    step = dash_len + gap_len
    start = -(phase % step)
    d = start
    while d < dist:
        seg_start = max(d, 0.0)
        seg_end = min(d + dash_len, dist)
        if seg_end > seg_start:
            a = np1 + direction * seg_start
            b = np1 + direction * seg_end
            cv2.line(img, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), color, thickness, cv2.LINE_AA)
        d += step


def draw_glow_circle(
    img: np.ndarray,
    center: Tuple[float, float],
    radius: float,
    color: Color,
    intensity: float = 1.0,
) -> None:
    """Renders a soft multi-ring glowing circle."""
    overlay = img.copy()
    cx, cy = int(center[0]), int(center[1])
    for r, a in [(radius * 2.2, 0.10), (radius * 1.5, 0.18), (radius, 0.35)]:
        cv2.circle(overlay, (cx, cy), int(r), color, -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.5 * intensity, img, 1.0 - 0.5 * intensity, 0, img)
    cv2.circle(img, (cx, cy), max(2, int(radius * 0.55)), color, -1, cv2.LINE_AA)


def draw_pin_marker(
    img: np.ndarray,
    pos: Tuple[float, float],
    color: Color,
    scale: float = 1.0,
    pulse: float = 0.0,
) -> None:
    """Renders a waypoint pin marker with animated pulsing ring."""
    x, y = int(pos[0]), int(pos[1])
    r = int(9 * scale)
    stem = int(16 * scale)
    pts = np.array([
        [x, y + stem],
        [x - r, y + stem - r],
        [x - r, y + stem - 2 * r],
        [x, y + stem - int(2.6 * r)],
        [x + r, y + stem - 2 * r],
        [x + r, y + stem - r],
    ], dtype=np.int32)
    overlay = img.copy()
    cv2.fillPoly(overlay, [pts], color, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.85, img, 0.15, 0, img)
    cv2.polylines(img, [pts], True, Palette.WHITE, 1, cv2.LINE_AA)
    pulse_r = int(r * (1.3 + pulse * 1.4))
    cv2.circle(img, (x, y + stem - 2 * r), pulse_r, color, 1, cv2.LINE_AA)
    cv2.circle(img, (x, y + stem - 2 * r), max(2, int(r * 0.4)), Palette.WHITE, -1, cv2.LINE_AA)


def rounded_rect(
    img: np.ndarray,
    pt1: Tuple[int, int],
    pt2: Tuple[int, int],
    color: Color,
    thickness: int = -1,
    radius: int = 10,
    alpha: float = 1.0,
) -> None:
    """Renders a rectangle with rounded corners and alpha transparency."""
    x1, y1 = pt1
    x2, y2 = pt2
    overlay = img.copy()
    if thickness < 0:
        cv2.rectangle(overlay, (x1 + radius, y1), (x2 - radius, y2), color, -1, cv2.LINE_AA)
        cv2.rectangle(overlay, (x1, y1 + radius), (x2, y2 - radius), color, -1, cv2.LINE_AA)
        for cx, cy in [
            (x1 + radius, y1 + radius),
            (x2 - radius, y1 + radius),
            (x1 + radius, y2 - radius),
            (x2 - radius, y2 - radius),
        ]:
            cv2.circle(overlay, (cx, cy), radius, color, -1, cv2.LINE_AA)
    else:
        cv2.rectangle(overlay, pt1, pt2, color, thickness, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, img, 1.0 - alpha, 0, img)


def put_text(
    img: np.ndarray,
    text: str,
    org: Tuple[int, int],
    scale: float = 0.5,
    color: Color = Palette.WHITE,
    thickness: int = 1,
    font: int = cv2.FONT_HERSHEY_SIMPLEX,
    glow: bool = False,
) -> None:
    """Renders text with optional black outline/glow for high readability."""
    if glow:
        cv2.putText(img, text, org, font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(img, text, org, font, scale, color, thickness, cv2.LINE_AA)


def frame_corners(
    img: np.ndarray,
    margin: int = 24,
    length: int = 26,
    color: Color = Palette.CYAN_SOFT,
    thickness: int = 2,
) -> None:
    """Draws HUD viewport corner brackets."""
    h, w = img.shape[:2]
    for (x, y, dx, dy) in [
        (margin, margin, 1, 1),
        (w - margin, margin, -1, 1),
        (margin, h - margin, 1, -1),
        (w - margin, h - margin, -1, -1),
    ]:
        cv2.line(img, (x, y), (x + dx * length, y), color, thickness, cv2.LINE_AA)
        cv2.line(img, (x, y), (x, y + dy * length), color, thickness, cv2.LINE_AA)


def scanline(
    img: np.ndarray,
    t_sec: float,
    speed: float = 0.35,
    color: Color = Palette.CYAN,
    alpha: float = 0.08,
) -> None:
    """Draws a moving horizontal scanline across the viewport."""
    h, w = img.shape[:2]
    y = int((math.sin(t_sec * speed) * 0.5 + 0.5) * h)
    overlay = img.copy()
    cv2.line(overlay, (0, y), (w, y), color, 1, cv2.LINE_AA)
    cv2.addWeighted(overlay, alpha, img, 1.0 - alpha, 0, img)
