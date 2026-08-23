"""3D perspective approach corridor geometry generation and smoothing."""

from typing import Dict, Optional, Tuple
import numpy as np

from skyvanta.core.types import ApproachCorridorGeometry
from skyvanta.core.config import SkyVantaConfig
from skyvanta.tracking.smoothing import Vec2EuroFilter


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_pt(p0: Tuple[float, float], p1: Tuple[float, float], t: float) -> Tuple[float, float]:
    return (lerp(p0[0], p1[0], t), lerp(p0[1], p1[1], t))


class ApproachCorridor:
    """Projects a trapezoidal 3D-style approach tunnel connecting the drone to the synthetic landing zone."""

    def __init__(self, frame_shape: Tuple[int, int], config: Optional[SkyVantaConfig] = None):
        self.h, self.w = frame_shape[:2]
        self.config = config or SkyVantaConfig()

        min_c = self.config.smoothing.corridor_min_cutoff
        beta = self.config.smoothing.corridor_beta

        self.filters: Dict[str, Vec2EuroFilter] = {
            k: Vec2EuroFilter(min_cutoff=min_c, beta=beta)
            for k in ["apex", "tl", "tr", "bl", "br"]
        }
        self.landing_center_filter = Vec2EuroFilter(min_cutoff=0.6, beta=beta)
        self.t_accum = 0.0

    def update(
        self,
        drone_center: Optional[Tuple[float, float]],
        drone_size: Optional[Tuple[float, float]],
        t_sec: float,
    ) -> ApproachCorridorGeometry:
        """Calculates smoothed perspective corner coordinates."""
        self.t_accum = t_sec
        if drone_center is None:
            drone_center = (self.w * 0.5, self.h * 0.28)
            drone_size = (self.w * 0.05, self.w * 0.05)

        cx, cy = drone_center
        sw, sh = drone_size
        apex = (cx, cy + sh * 0.55)

        closeness = clamp((sw * sh) / (0.02 * self.w * self.h), 0.0, 1.0)
        zone_y = lerp(self.h * 0.72, self.h * 0.90, closeness)
        zone_half_w = lerp(self.w * 0.16, self.w * 0.30, closeness)
        zone_depth = lerp(self.h * 0.10, self.h * 0.16, closeness)

        drift = (cx - self.w * 0.5) * 0.35
        zone_cx = clamp(self.w * 0.5 + drift, zone_half_w + 20.0, self.w - zone_half_w - 20.0)

        near_half = zone_half_w
        far_half = zone_half_w * 0.62
        tl = (zone_cx - far_half, zone_y - zone_depth * 0.5)
        tr = (zone_cx + far_half, zone_y - zone_depth * 0.5)
        bl = (zone_cx - near_half, zone_y + zone_depth * 0.5)
        br = (zone_cx + near_half, zone_y + zone_depth * 0.5)

        apex_s = self.filters["apex"](apex, t=t_sec)
        tl_s = self.filters["tl"](tl, t=t_sec)
        tr_s = self.filters["tr"](tr, t=t_sec)
        bl_s = self.filters["bl"](bl, t=t_sec)
        br_s = self.filters["br"](br, t=t_sec)
        center_s = self.landing_center_filter((zone_cx, zone_y), t=t_sec)

        return ApproachCorridorGeometry(
            apex=apex_s,
            tl=tl_s,
            tr=tr_s,
            bl=bl_s,
            br=br_s,
            center=center_s,
            closeness=float(closeness),
        )
