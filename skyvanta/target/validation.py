"""Corner validation and planar geometric verification for fiducial markers."""

import math
from typing import List, Optional, Tuple, Union
import numpy as np


class CornerValidator:
    """Validates geometric integrity, ordering, convexity, and area of 4-corner polygons."""

    def __init__(self, min_area_px: float = 16.0):
        self.min_area_px = float(min_area_px)

    def validate(
        self,
        corners: Union[np.ndarray, List[Tuple[float, float]]],
    ) -> Tuple[bool, Optional[str]]:
        """Evaluates whether the provided 4 corners form a valid, non-degenerate planar quadrilateral.

        Returns:
            (is_valid, error_reason)
        """
        pts = np.ascontiguousarray(corners, dtype=np.float64).reshape(-1, 2)

        # 1. Point count verification
        if len(pts) != 4:
            return False, f"Expected exactly 4 corners, received {len(pts)}"

        # 2. Finite value verification
        if not np.all(np.isfinite(pts)):
            return False, "Corners contain non-finite values (NaN or Inf)"

        # 3. Duplicate vertex check
        for i in range(4):
            for j in range(i + 1, 4):
                dist = math.hypot(pts[i, 0] - pts[j, 0], pts[i, 1] - pts[j, 1])
                if dist < 1.0:
                    return False, f"Duplicate or overlapping corners detected at index {i} and {j}"

        # 4. Enclosed area calculation (Shoelace formula)
        area = 0.5 * abs(
            pts[0, 0] * pts[1, 1] + pts[1, 0] * pts[2, 1] + pts[2, 0] * pts[3, 1] + pts[3, 0] * pts[0, 1]
            - (pts[1, 0] * pts[0, 1] + pts[2, 0] * pts[1, 1] + pts[3, 0] * pts[2, 1] + pts[0, 0] * pts[3, 1])
        )

        if area < self.min_area_px:
            return False, f"Corner enclosed area {area:.1f}px² is below minimum threshold {self.min_area_px:.1f}px²"

        # 5. Strict Convexity check (all consecutive cross-products must share the same sign)
        cross_products = []
        for i in range(4):
            p1 = pts[i]
            p2 = pts[(i + 1) % 4]
            p3 = pts[(i + 2) % 4]
            v1 = p2 - p1
            v2 = p3 - p2
            cp = v1[0] * v2[1] - v1[1] * v2[0]
            cross_products.append(cp)

        signs = [math.copysign(1.0, cp) for cp in cross_products if abs(cp) > 1e-4]
        if len(signs) < 4:
            return False, "Collinear adjacent edges detected in quadrilateral"

        if not (all(s > 0 for s in signs) or all(s < 0 for s in signs)):
            return False, "Quadrilateral is self-intersecting or concave (non-convex)"

        return True, None
