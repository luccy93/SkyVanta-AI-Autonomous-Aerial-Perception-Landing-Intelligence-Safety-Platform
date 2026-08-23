"""Procedural synthetic scene and target trajectory generator for testing and standalone demos."""

import math
from typing import Generator, Optional, Tuple
import cv2
import numpy as np


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def generate_synthetic_background(w: int = 1280, h: int = 720, seed: int = 7) -> np.ndarray:
    """Procedurally renders an aerial terrain scene with sky, cloud layers, fields, and road."""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3), dtype=np.float32)

    horizon = int(h * 0.42)
    sky_top = np.array([225, 190, 150], dtype=np.float32)
    sky_horizon = np.array([205, 195, 190], dtype=np.float32)
    for y in range(horizon):
        t = y / max(1, horizon)
        img[y, :] = sky_top * (1.0 - t) + sky_horizon * t

    cloud_layer = np.zeros((horizon, w), dtype=np.float32)
    for _ in range(14):
        cx = rng.uniform(0, w)
        cy = rng.uniform(0, horizon * 0.8)
        rx = rng.uniform(w * 0.08, w * 0.22)
        ry = rng.uniform(h * 0.02, h * 0.05)
        yy, xx = np.mgrid[0:horizon, 0:w]
        cloud_layer += np.exp(-(((xx - cx) ** 2) / (2.0 * rx ** 2) + ((yy - cy) ** 2) / (2.0 * ry ** 2))) * rng.uniform(15, 35)
    cloud_layer = np.clip(cloud_layer, 0, 40)
    for c in range(3):
        img[:horizon, :, c] += cloud_layer

    ground = np.zeros((h - horizon, w, 3), dtype=np.float32)
    field_h, field_w = ground.shape[0], ground.shape[1]
    base_greens = [
        np.array([70, 145, 80]),
        np.array([60, 130, 70]),
        np.array([85, 150, 95]),
        np.array([55, 120, 60]),
        np.array([95, 140, 70]),
    ]
    n_rows = 5
    row_bounds = np.linspace(0, field_h, n_rows + 1)
    for ri in range(n_rows):
        y0, y1 = int(row_bounds[ri]), int(row_bounds[ri + 1])
        depth_t = ri / max(1, n_rows - 1)
        n_cols = 3 + ri
        col_bounds = np.linspace(0, field_w, max(2, n_cols) + 1)

        jitter = rng.uniform(-field_w * 0.02, field_w * 0.02, col_bounds.shape)
        jitter[0] = 0.0
        jitter[-1] = 0.0
        col_bounds = np.clip(col_bounds + jitter, 0, field_w)
        col_bounds.sort()
        col_bounds[0] = 0.0
        col_bounds[-1] = field_w
        for ci in range(len(col_bounds) - 1):
            x0, x1 = int(col_bounds[ci]), int(col_bounds[ci + 1])
            if x1 <= x0:
                continue
            color = base_greens[(ri + ci) % len(base_greens)].astype(np.float32)
            haze = 1.0 - depth_t * 0.35
            color = color * haze + np.array([200, 195, 185]) * (1.0 - haze)
            ground[y0:y1, x0:x1] = color
            n_lines = rng.integers(3, 7)
            for _ in range(n_lines):
                ly = rng.integers(y0, max(y0 + 1, y1))
                shade = rng.uniform(-14, 10)
                ground[ly:ly + 1, x0:x1] += shade

    road_top_x = w * 0.5 + rng.uniform(-w * 0.03, w * 0.03)
    road_bot_x0 = w * 0.40
    road_bot_x1 = w * 0.60
    yy, xx = np.mgrid[0:field_h, 0:field_w]
    t_row = yy / max(1, field_h - 1)
    left_edge = road_top_x + (road_bot_x0 - road_top_x) * t_row - field_w * 0.03
    right_edge = road_top_x + (road_bot_x1 - road_top_x) * t_row + field_w * 0.03
    road_mask = (xx >= left_edge) & (xx <= right_edge)
    road_color = np.array([110, 150, 165], dtype=np.float32)
    for c in range(3):
        ground[..., c] = np.where(road_mask, ground[..., c] * 0.25 + road_color[c] * 0.75, ground[..., c])

    img[horizon:, :] = ground

    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h / 2.0, w / 2.0
    dist = np.sqrt(((xx - cx) / (w / 2.0)) ** 2 + ((yy - cy) / (h / 2.0)) ** 2)
    vignette = 1.0 - np.clip(dist - 0.55, 0, 1) * 0.35
    for c in range(3):
        img[..., c] *= vignette

    noise = rng.normal(0, 4.5, (h, w, 3))
    img = np.clip(img + noise, 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(img, (3, 3), 0)


def apply_zoom_pan(img: np.ndarray, zoom: float, dx: int, dy: int) -> np.ndarray:
    """Applies camera zoom and translational panning to an aerial background image."""
    h, w = img.shape[:2]
    new_w, new_h = int(w * zoom), int(h * zoom)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    x0 = clamp((new_w - w) // 2 + dx, 0, max(0, new_w - w))
    y0 = clamp((new_h - h) // 2 + dy, 0, max(0, new_h - h))
    return resized[int(y0):int(y0 + h), int(x0):int(x0 + w)]


class SyntheticSceneGenerator:
    """Generates procedural demo video frames and target trajectory ground truth."""

    def __init__(self, width: int = 1280, height: int = 720, fps: float = 30.0, duration_sec: float = 13.0):
        self.w = width
        self.h = height
        self.fps = fps
        self.duration_sec = duration_sec
        self.n_frames = int(duration_sec * fps)
        self.bg = generate_synthetic_background(width, height)

        rng = np.random.default_rng(42)
        wobble_x = rng.normal(0, 1, self.n_frames).cumsum()
        self.wobble_x = wobble_x / (np.max(np.abs(wobble_x)) + 1e-6)
        wobble_y = rng.normal(0, 1, self.n_frames).cumsum()
        self.wobble_y = wobble_y / (np.max(np.abs(wobble_y)) + 1e-6)

        self.start = (self.w * 0.28, self.h * 0.20)
        self.end = (self.w * 0.52, self.h * 0.40)
        self.drone_start_size = (self.w * 0.045, self.w * 0.045 * 0.55)
        self.drone_end_size = (self.w * 0.085, self.w * 0.085 * 0.55)

    def generate_frames(self) -> Generator[Tuple[int, float, np.ndarray, Tuple[float, float, float, float], bool], None, None]:
        """Yields (frame_idx, t_sec, frame_bgr, (cx, cy, sw, sh), present_flag)."""
        zoom_amt = 0.06
        for i in range(self.n_frames):
            t = i / max(1, self.n_frames - 1)
            t_sec = i / self.fps
            search_phase = t_sec < 1.2

            te = ease(clamp((t_sec - 0.3) / (self.duration_sec - 0.6), 0.0, 1.0))
            cx = lerp(self.start[0], self.end[0], te) + self.wobble_x[i] * self.w * 0.015
            cy = lerp(self.start[1], self.end[1], te) + self.wobble_y[i] * self.h * 0.012
            sw = lerp(self.drone_start_size[0], self.drone_end_size[0], te)
            sh = lerp(self.drone_start_size[1], self.drone_end_size[1], te)

            zt = ease(t)
            z = 1.0 + zoom_amt * zt
            drift_x = int(self.w * 0.02 * math.sin(t_sec * 0.25))
            drift_y = int(self.h * 0.01 * math.cos(t_sec * 0.20))
            frame = apply_zoom_pan(self.bg, z, drift_x, drift_y)

            yield i, t_sec, frame, (cx, cy, sw, sh), not search_phase
