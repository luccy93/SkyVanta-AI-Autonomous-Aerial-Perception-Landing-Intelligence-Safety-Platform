"""Deterministic discrete simulation clock for Digital Twin execution."""

from typing import Optional


class SimulationClock:
    """Manages deterministic discrete simulation time."""

    def __init__(self, start_time_sec: float = 0.0, default_dt_sec: float = 0.05):
        self._start_time_sec: float = float(start_time_sec)
        self._current_time_sec: float = float(start_time_sec)
        self._default_dt_sec: float = float(default_dt_sec)
        self._step_count: int = 0
        self._is_paused: bool = False

    @property
    def current_time_sec(self) -> float:
        """Returns the current simulation epoch time in seconds."""
        return self._current_time_sec

    @property
    def step_count(self) -> int:
        """Returns the total number of discrete simulation steps executed."""
        return self._step_count

    @property
    def dt_sec(self) -> float:
        """Returns default simulation timestep."""
        return self._default_dt_sec

    @property
    def is_paused(self) -> bool:
        """Returns True if the clock is paused."""
        return self._is_paused

    def step(self, dt_sec: Optional[float] = None) -> float:
        """Advances the simulation clock by dt_sec if not paused.

        Args:
            dt_sec: Optional custom timestep in seconds (defaults to default_dt_sec).

        Returns:
            New current simulation time in seconds.
        """
        if self._is_paused:
            return self._current_time_sec

        step_size = self._default_dt_sec if dt_sec is None else float(dt_sec)
        if step_size < 0.0:
            raise ValueError(f"Timestep must be non-negative (got {step_size})")

        self._current_time_sec += step_size
        self._step_count += 1
        return self._current_time_sec

    def pause(self) -> None:
        """Pauses the clock; subsequent step() calls will not advance time."""
        self._is_paused = True

    def resume(self) -> None:
        """Resumes advancing time on step() calls."""
        self._is_paused = False

    def reset(self, start_time_sec: Optional[float] = None) -> None:
        """Resets the clock to initial or specified start time."""
        if start_time_sec is not None:
            self._start_time_sec = float(start_time_sec)
        self._current_time_sec = self._start_time_sec
        self._step_count = 0
        self._is_paused = False
