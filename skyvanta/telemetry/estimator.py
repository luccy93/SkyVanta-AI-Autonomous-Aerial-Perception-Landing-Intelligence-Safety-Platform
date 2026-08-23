"""Visual telemetry heuristics and relative offset estimations.

DISCLAIMER: In Volume 1, telemetry values are visual estimations derived
from 2D bounding box geometry, scale expansion, and pixel offsets.
They are NOT calibrated 3D poses or certified flight sensors.
"""

import math
from typing import Optional, Tuple
from skyvanta.core.types import TelemetryEstimate
from skyvanta.core.config import SkyVantaConfig
from skyvanta.tracking.smoothing import OneEuroFilter


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


class TelemetryEstimator:
    """Estimates distance, altitude, angle, alignment, and landing confidence from 2D tracks."""

    def __init__(self, frame_shape: Tuple[int, int], config: Optional[SkyVantaConfig] = None):
        self.h, self.w = frame_shape[:2]
        self.config = config or SkyVantaConfig()

        min_c = self.config.smoothing.telemetry_min_cutoff
        beta = self.config.smoothing.telemetry_beta

        self.f_distance = OneEuroFilter(min_cutoff=min_c, beta=beta)
        self.f_altitude = OneEuroFilter(min_cutoff=min_c, beta=beta)
        self.f_angle = OneEuroFilter(min_cutoff=min_c, beta=beta)
        self.f_align = OneEuroFilter(min_cutoff=min_c, beta=beta)
        self.f_lat = OneEuroFilter(min_cutoff=min_c, beta=beta)
        self.f_vert = OneEuroFilter(min_cutoff=min_c, beta=beta)
        self.f_conf = OneEuroFilter(min_cutoff=0.6, beta=beta)

    def estimate(
        self,
        center: Optional[Tuple[float, float]],
        size: Optional[Tuple[float, float]],
        track_conf: float,
        scale_trend: float,
        t_sec: float,
    ) -> Optional[TelemetryEstimate]:
        """Calculates smoothed visual telemetry estimates for HUD readouts."""
        if center is None or size is None:
            return None

        cx, cy = center
        sw, sh = size
        diag = math.sqrt(sw * sw + sh * sh)
        ref_diag = 0.05 * math.sqrt(self.w ** 2 + self.h ** 2)

        # Distance heuristic based on apparent pixel diagonal
        raw_distance = clamp(ref_diag / max(diag, 1e-3) * 8.0, 3.0, 120.0)
        distance = self.f_distance(raw_distance, t=t_sec)

        # Altitude heuristic based on screen vertical position
        norm_y = 1.0 - clamp(cy / self.h, 0.0, 1.0)
        raw_altitude = 2.0 + norm_y * 40.0 + scale_trend * 3.0
        altitude = self.f_altitude(raw_altitude, t=t_sec)

        # Approach angle heuristic based on horizontal displacement
        norm_x_off = (cx - self.w / 2.0) / (self.w / 2.0)
        raw_angle = clamp(norm_x_off * 12.0, -25.0, 25.0)
        angle = self.f_angle(raw_angle, t=t_sec)

        # Alignment percentage heuristic
        raw_align = clamp(100.0 - abs(norm_x_off) * 60.0 - abs(angle) * 0.8, 30.0, 99.0)
        align = self.f_align(raw_align, t=t_sec)

        # Lateral and vertical pixel-derived offset estimates
        raw_lat = norm_x_off * 3.2
        lateral = self.f_lat(raw_lat, t=t_sec)

        norm_y_off = (cy - self.h * 0.4) / (self.h * 0.5)
        raw_vert = clamp(norm_y_off * 2.5, -4.0, 4.0)
        vertical = self.f_vert(raw_vert, t=t_sec)

        # Composite landing confidence
        raw_conf = clamp(track_conf * 100.0 * (0.6 + 0.4 * (1.0 - abs(norm_x_off))), 0.0, 99.0)
        landing_conf = self.f_conf(raw_conf, t=t_sec)

        return TelemetryEstimate(
            estimated_distance_m=float(distance),
            estimated_altitude_m=float(altitude),
            estimated_approach_angle_deg=float(angle),
            estimated_alignment_pct=float(align),
            estimated_lateral_offset_m=float(lateral),
            estimated_vertical_offset_m=float(vertical),
            landing_confidence_pct=float(landing_conf),
        )
