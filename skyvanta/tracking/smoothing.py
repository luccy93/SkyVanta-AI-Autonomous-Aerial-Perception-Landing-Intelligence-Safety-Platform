"""One Euro adaptive low-pass filter implementations for jitter removal."""

import math
import time
from typing import Optional, Tuple


class OneEuroFilter:
    """1D adaptive low-pass filter with velocity-dependent cutoff frequency."""

    def __init__(
        self,
        freq: float = 30.0,
        min_cutoff: float = 1.0,
        beta: float = 0.015,
        d_cutoff: float = 1.0,
    ):
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev: Optional[float] = None
        self.dx_prev: float = 0.0
        self.t_prev: Optional[float] = None

    @staticmethod
    def _alpha(cutoff: float, freq: float) -> float:
        te = 1.0 / freq
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / te)

    def __call__(self, x: float, t: Optional[float] = None) -> float:
        if t is None:
            t = time.time()
        if self.t_prev is None:
            self.t_prev = t

        dt = max(t - self.t_prev, 1e-3)
        self.freq = 1.0 / dt if dt > 0 else self.freq
        self.t_prev = t

        if self.x_prev is None:
            self.x_prev = x
            self.dx_prev = 0.0
            return x

        dx = (x - self.x_prev) * self.freq
        a_d = self._alpha(self.d_cutoff, self.freq)
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff, self.freq)
        x_hat = a * x + (1.0 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        return x_hat

    def reset(self) -> None:
        """Resets filter memory."""
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None


class Vec2EuroFilter:
    """2D One Euro filter applied independently to x and y coordinates."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.015, freq: float = 30.0):
        self.fx = OneEuroFilter(freq=freq, min_cutoff=min_cutoff, beta=beta)
        self.fy = OneEuroFilter(freq=freq, min_cutoff=min_cutoff, beta=beta)

    def __call__(self, pt: Tuple[float, float], t: Optional[float] = None) -> Tuple[float, float]:
        return (self.fx(pt[0], t), self.fy(pt[1], t))

    def reset(self) -> None:
        """Resets both x and y filters."""
        self.fx.reset()
        self.fy.reset()
