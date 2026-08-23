"""HUD graphics compositor and tactical overlays for SkyVanta AI."""

import math
import time
from collections import deque
from typing import Deque, Optional, Tuple
import cv2
import numpy as np

from skyvanta.core.types import (
    TrackState,
    TrackInfo,
    TelemetryEstimate,
    ApproachCorridorGeometry,
)
from skyvanta.core.config import SkyVantaConfig
from skyvanta.tracking.smoothing import OneEuroFilter
from skyvanta.visualization.palette import Palette
from skyvanta.visualization.drawing import (
    draw_dashed_line,
    draw_glow_circle,
    draw_pin_marker,
    rounded_rect,
    put_text,
    frame_corners,
    scanline,
)


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_pt(p0: Tuple[float, float], p1: Tuple[float, float], t: float) -> Tuple[float, float]:
    return (lerp(p0[0], p1[0], t), lerp(p0[1], p1[1], t))


class HUDRenderer:
    """Renders tactical HUD overlays, approach corridors, radar, and telemetry readouts."""

    def __init__(self, frame_shape: Tuple[int, int], config: Optional[SkyVantaConfig] = None):
        self.h, self.w = frame_shape[:2]
        self.config = config or SkyVantaConfig()
        self.fps_target = self.config.visualization.fps_target
        self.frame_margin = self.config.visualization.frame_margin

        self.t0 = time.time()
        self.frame_count = 0
        self._fps_smooth = self.fps_target
        self._radar_history: Deque[Tuple[float, float]] = deque(maxlen=60)
        self.corridor_alpha_f = OneEuroFilter(min_cutoff=0.5, beta=0.02)
        self.zone_scan_phase = 0.0

    def render(
        self,
        frame: np.ndarray,
        track_info: TrackInfo,
        telemetry: Optional[TelemetryEstimate],
        corridor: Optional[ApproachCorridorGeometry],
        t_sec: float,
        real_fps: Optional[float] = None,
    ) -> np.ndarray:
        """Composites full multi-layer HUD overlays onto the video frame."""
        out = frame.copy()
        overlay_full = np.zeros_like(out)

        visible = track_info.is_visible
        conf = track_info.confidence
        pulse = 0.5 + 0.5 * math.sin(t_sec * 3.2)

        if corridor and self.config.visualization.show_corridor:
            self._draw_corridor(overlay_full, corridor, visible, conf, t_sec)

        alpha_target = 0.85 if visible else 0.35
        alpha = self.corridor_alpha_f(alpha_target, t=t_sec)
        cv2.addWeighted(overlay_full, alpha, out, 1.0, 0, out)

        if visible and track_info.bbox and track_info.center:
            self._draw_drone_box(out, track_info, t_sec, pulse)

        scanline(out, t_sec)
        self._draw_vignette_frame(out)
        self._draw_top_left(out, track_info, real_fps)
        self._draw_top_right(out, track_info, telemetry)

        if self.config.visualization.show_telemetry:
            self._draw_bottom_left(out, telemetry)

        if corridor and self.config.visualization.show_radar:
            self._draw_radar_panel(out, track_info, corridor, t_sec)

        self.frame_count += 1
        return out

    def _draw_corridor(
        self,
        img: np.ndarray,
        corridor: ApproachCorridorGeometry,
        visible: bool,
        conf: float,
        t_sec: float,
    ) -> None:
        apex, tl, tr, bl, br = corridor.apex, corridor.tl, corridor.tr, corridor.bl, corridor.br
        closeness = corridor.closeness

        base_alpha = 0.16 + 0.10 * closeness
        color = Palette.CYAN if visible else Palette.WHITE_DIM

        poly_left = np.array([apex, tl, bl], dtype=np.int32)
        poly_right = np.array([apex, tr, br], dtype=np.int32)
        poly_far = np.array([tl, tr, br, bl], dtype=np.int32)

        fill = img.copy()
        cv2.fillPoly(fill, [poly_left], color, cv2.LINE_AA)
        cv2.fillPoly(fill, [poly_right], color, cv2.LINE_AA)
        cv2.fillPoly(fill, [poly_far], Palette.GREEN, cv2.LINE_AA)
        cv2.addWeighted(fill, base_alpha, img, 1.0 - base_alpha, 0, img)

        phase = (t_sec * 40.0) % 200.0
        draw_dashed_line(img, apex, tl, color, 2, 12, 8, phase)
        draw_dashed_line(img, apex, tr, color, 2, 12, 8, phase)
        draw_dashed_line(img, apex, bl, color, 2, 12, 8, phase * 0.8)
        draw_dashed_line(img, apex, br, color, 2, 12, 8, phase * 0.8)

        mid_far = lerp_pt(tl, tr, 0.5)
        mid_near = lerp_pt(bl, br, 0.5)
        cv2.line(img, (int(apex[0]), int(apex[1])), (int(mid_near[0]), int(mid_near[1])), Palette.WHITE, 1, cv2.LINE_AA)
        draw_dashed_line(img, mid_far, mid_near, Palette.CYAN_SOFT, 1, 6, 6, phase)

        for f in (0.33, 0.66):
            l = lerp_pt(apex, bl, f)
            r = lerp_pt(apex, br, f)
            draw_dashed_line(img, l, r, Palette.TEAL, 1, 8, 6, phase)

        self.zone_scan_phase = (self.zone_scan_phase + 2.4) % 300.0
        draw_dashed_line(img, tl, tr, Palette.GREEN, 2, 10, 6, self.zone_scan_phase)
        draw_dashed_line(img, tr, br, Palette.GREEN, 2, 10, 6, self.zone_scan_phase)
        draw_dashed_line(img, br, bl, Palette.GREEN, 2, 10, 6, self.zone_scan_phase)
        draw_dashed_line(img, bl, tl, Palette.GREEN, 2, 10, 6, self.zone_scan_phase)

        for f in (0.33, 0.66):
            a = lerp_pt(tl, bl, f)
            b = lerp_pt(tr, br, f)
            cv2.line(img, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), Palette.GREEN_DIM, 1, cv2.LINE_AA)
        for f in (0.33, 0.66):
            a = lerp_pt(tl, tr, f)
            b = lerp_pt(bl, br, f)
            cv2.line(img, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), Palette.GREEN_DIM, 1, cv2.LINE_AA)

        sweep_t = (math.sin(t_sec * 1.1) + 1.0) / 2.0
        sweep_l = lerp_pt(tl, bl, sweep_t)
        sweep_r = lerp_pt(tr, br, sweep_t)
        cv2.line(img, (int(sweep_l[0]), int(sweep_l[1])), (int(sweep_r[0]), int(sweep_r[1])), Palette.GREEN, 2, cv2.LINE_AA)

        pulse = 0.5 + 0.5 * math.sin(t_sec * 3.0)
        for corner in (tl, tr, bl, br):
            draw_pin_marker(img, corner, Palette.GREEN, scale=0.85, pulse=pulse)

        center = corridor.center
        label = "LANDING ZONE"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        put_text(img, label, (int(center[0] - tw / 2), int(center[1] + th / 2)), 0.45, Palette.WHITE, 1, glow=True)

    def _draw_drone_box(self, img: np.ndarray, track: TrackInfo, t_sec: float, pulse: float) -> None:
        if track.bbox is None or track.center is None:
            return

        x1, y1, x2, y2 = [int(v) for v in track.bbox.to_tuple()]
        color = Palette.CYAN
        L = max(10, int((x2 - x1) * 0.18))
        thick = 2

        for (px, py, dx, dy) in [
            (x1, y1, 1, 1),
            (x2, y1, -1, 1),
            (x1, y2, 1, -1),
            (x2, y2, -1, -1),
        ]:
            cv2.line(img, (px, py), (px + dx * L, py), color, thick, cv2.LINE_AA)
            cv2.line(img, (px, py), (px, py + dy * L), color, thick, cv2.LINE_AA)

        cv2.rectangle(img, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)

        cx, cy = track.center
        cv2.circle(img, (int(cx), int(cy)), 2, Palette.WHITE, -1, cv2.LINE_AA)
        ring_r = int(6 + 3 * pulse)
        cv2.circle(img, (int(cx), int(cy)), ring_r, color, 1, cv2.LINE_AA)

        label = f"DRONE #{track.track_id}  {track.state.value}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        ly = max(18, y1 - 10)
        rounded_rect(img, (x1 - 4, ly - th - 8), (x1 + tw + 8, ly + 4), Palette.BG_PANEL, -1, 6, 0.55)
        put_text(img, label, (x1, ly), 0.5, color, 1)

    def _draw_vignette_frame(self, img: np.ndarray) -> None:
        h, w = self.h, self.w
        overlay = img.copy()
        cv2.rectangle(overlay, (0, 0), (w, 78), (0, 0, 0), -1)
        cv2.rectangle(overlay, (0, h - 60), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)

        frame_corners(img, margin=self.frame_margin, length=26, color=Palette.CYAN_SOFT, thickness=2)

    def _draw_top_left(self, img: np.ndarray, track: TrackInfo, real_fps: Optional[float]) -> None:
        x, y = self.frame_margin + 14, 30
        put_text(img, "DRONE LANDING PERCEPTION", (x, y), 0.62, Palette.WHITE, 2, glow=True)
        y += 22
        fps = real_fps if real_fps else self.fps_target
        self._fps_smooth = lerp(self._fps_smooth, fps, 0.1)
        put_text(img, f"FPS {self._fps_smooth:4.1f}   FRAME {self.frame_count:05d}", (x, y), 0.42, Palette.WHITE_DIM, 1, glow=True)
        y += 18

        state_colors = {
            TrackState.SEARCHING: Palette.AMBER,
            TrackState.ACQUIRED: Palette.AMBER,
            TrackState.TRACKING: Palette.CYAN,
            TrackState.LOCKED: Palette.GREEN,
            TrackState.APPROACHING: Palette.GREEN,
        }
        state_color = state_colors.get(track.state, Palette.WHITE)
        put_text(img, f"TRACKING STATUS: {track.state.value}", (x, y), 0.46, state_color, 1, glow=True)
        y += 18
        put_text(img, f"TRACK ID: {track.track_id}", (x, y), 0.42, Palette.WHITE_DIM, 1, glow=True)

    def _draw_top_right(self, img: np.ndarray, track: TrackInfo, telemetry: Optional[TelemetryEstimate]) -> None:
        w = self.w
        x = w - self.frame_margin - 14
        y = 30
        is_locked = track.state in (TrackState.LOCKED, TrackState.APPROACHING)
        lock_txt = "TARGET LOCK: YES" if is_locked else "TARGET LOCK: NO"
        lock_color = Palette.GREEN if is_locked else Palette.AMBER
        (tw, _), _ = cv2.getTextSize(lock_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        put_text(img, lock_txt, (x - tw, y), 0.5, lock_color, 1, glow=True)
        y += 22

        conf_pct = track.confidence * 100.0
        bar_label = f"CONFIDENCE {conf_pct:5.1f}%"
        (tw, _), _ = cv2.getTextSize(bar_label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        put_text(img, bar_label, (x - tw, y), 0.42, Palette.WHITE_DIM, 1, glow=True)
        bar_w, bar_h = 120, 6
        bx2 = x
        bx1 = bx2 - bar_w
        by1 = y + 6
        cv2.rectangle(img, (bx1, by1), (bx2, by1 + bar_h), Palette.GRID, 1, cv2.LINE_AA)
        fill_w = int(bar_w * clamp(track.confidence, 0.0, 1.0))
        if fill_w > 0:
            cv2.rectangle(img, (bx1, by1), (bx1 + fill_w, by1 + bar_h), Palette.CYAN, -1, cv2.LINE_AA)
        y += 22

        align_val = telemetry.estimated_alignment_pct if telemetry else 0.0
        align_txt = f"ALIGNMENT {align_val:5.1f}%"
        (tw, _), _ = cv2.getTextSize(align_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        put_text(img, align_txt, (x - tw, y), 0.42, Palette.WHITE_DIM, 1, glow=True)
        y += 20

        landing_state = track.state.value if track.state != TrackState.SEARCHING else "IDLE"
        ls_txt = f"LANDING STATE: {landing_state}"
        (tw, _), _ = cv2.getTextSize(ls_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
        put_text(img, ls_txt, (x - tw, y), 0.42, Palette.WHITE_DIM, 1, glow=True)

    def _draw_bottom_left(self, img: np.ndarray, telemetry: Optional[TelemetryEstimate]) -> None:
        x = self.frame_margin + 14
        y = self.h - 128
        panel_w = 250
        rounded_rect(img, (x - 10, y - 20), (x + panel_w, self.h - 16), Palette.BG_PANEL, -1, 8, 0.45)
        put_text(img, "TELEMETRY (EST.)", (x, y), 0.42, Palette.CYAN_SOFT, 1)
        y += 18

        if telemetry is None:
            put_text(img, "-- NO TARGET --", (x, y), 0.42, Palette.WHITE_DIM, 1)
            return

        rows = [
            ("DISTANCE", f"{telemetry.estimated_distance_m:5.1f} m"),
            ("ALTITUDE", f"{telemetry.estimated_altitude_m:5.1f} m"),
            ("APPROACH ANGLE", f"{telemetry.estimated_approach_angle_deg:+5.1f} deg"),
            ("ALIGNMENT", f"{telemetry.estimated_alignment_pct:5.1f}%"),
            ("LATERAL OFFSET", f"{telemetry.estimated_lateral_offset_m:+4.2f} m"),
            ("VERTICAL OFFSET", f"{telemetry.estimated_vertical_offset_m:+4.2f} m"),
            ("LANDING CONFIDENCE", f"{telemetry.landing_confidence_pct:5.1f}%"),
        ]
        for label, val in rows:
            put_text(img, label, (x, y), 0.37, Palette.WHITE_DIM, 1)
            (tw, _), _ = cv2.getTextSize(val, cv2.FONT_HERSHEY_SIMPLEX, 0.37, 1)
            put_text(img, val, (x + panel_w - 20 - tw, y), 0.37, Palette.WHITE, 1)
            y += 15

    def _draw_radar_panel(
        self,
        img: np.ndarray,
        track: TrackInfo,
        corridor: ApproachCorridorGeometry,
        t_sec: float,
    ) -> None:
        w, h = self.w, self.h
        panel_size = 150
        px2, py2 = w - self.frame_margin - 14, h - 16
        px1, py1 = px2 - panel_size, py2 - panel_size

        rounded_rect(img, (px1, py1), (px2, py2), Palette.BG_PANEL, -1, 8, 0.5)
        cv2.rectangle(img, (px1, py1), (px2, py2), Palette.GRID, 1, cv2.LINE_AA)
        put_text(img, "APPROACH RADAR", (px1 + 8, py1 + 16), 0.35, Palette.CYAN_SOFT, 1)

        cx, cy = px1 + panel_size // 2, py1 + panel_size // 2 + 12
        max_r = panel_size // 2 - 24
        for rr in (max_r, int(max_r * 0.66), int(max_r * 0.33)):
            cv2.circle(img, (cx, cy), rr, Palette.GRID, 1, cv2.LINE_AA)
        cv2.line(img, (cx - max_r, cy), (cx + max_r, cy), Palette.GRID, 1, cv2.LINE_AA)
        cv2.line(img, (cx, cy - max_r), (cx, cy + max_r), Palette.GRID, 1, cv2.LINE_AA)

        sweep_ang = (t_sec * 90.0) % 360.0
        ex = cx + int(max_r * math.cos(math.radians(sweep_ang)))
        ey = cy + int(max_r * math.sin(math.radians(sweep_ang)))
        overlay = img.copy()
        cv2.line(overlay, (cx, cy), (ex, ey), Palette.GREEN, 1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.5, img, 0.5, 0, img)

        tx, ty = cx, cy + max_r - 6
        cv2.drawMarker(img, (tx, ty), Palette.GREEN, cv2.MARKER_TRIANGLE_UP, 8, 2)

        if track.is_visible and track.center:
            dc = track.center
            zc = corridor.center
            rel_x = (dc[0] - zc[0]) / (self.w * 0.35)
            rel_y = (dc[1] - zc[1]) / (self.h * 0.35)
            rx = clamp(cx + rel_x * max_r, px1 + 6.0, px2 - 6.0)
            ry = clamp(cy + rel_y * max_r, py1 + 20.0, py2 - 6.0)
            self._radar_history.append((rx, ry))

        pts = list(self._radar_history)
        for i in range(1, len(pts)):
            t = i / max(1, len(pts))
            color = tuple(int(c * (0.2 + 0.5 * t)) for c in Palette.CYAN)
            cv2.line(img, (int(pts[i - 1][0]), int(pts[i - 1][1])), (int(pts[i][0]), int(pts[i][1])), color, 1, cv2.LINE_AA)
        if pts:
            pulse = 0.5 + 0.5 * math.sin(t_sec * 4.0)
            draw_glow_circle(img, pts[-1], 3.0 + pulse, Palette.CYAN, 0.8)
