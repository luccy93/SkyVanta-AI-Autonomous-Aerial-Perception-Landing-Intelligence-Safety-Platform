"""Tiered token-bucket rate limiting for API endpoint and workload protection."""

from enum import Enum
import threading
import time
from typing import Dict, Optional, Tuple


class RateLimitTier(str, Enum):
    """Rate limit categories based on resource intensity."""
    READ = "read"          # Scenario catalog, system info
    EXECUTE = "execute"    # 6-DoF Simulation runs
    METRICS = "metrics"    # Operational metrics inspection


class TieredTokenBucketRateLimiter:
    """Thread-safe, tiered token bucket rate limiter with bounded memory."""

    def __init__(
        self,
        read_rate_per_min: int = 120,
        read_burst: int = 30,
        execute_rate_per_min: int = 30,
        execute_burst: int = 10,
        metrics_rate_per_min: int = 60,
        metrics_burst: int = 20,
        max_clients: int = 10000,
    ):
        self._lock = threading.RLock()
        self.max_clients = max_clients

        # Configuration per tier: (fill_rate_per_sec, max_tokens)
        self._tier_configs: Dict[RateLimitTier, Tuple[float, float]] = {
            RateLimitTier.READ: (read_rate_per_min / 60.0, float(read_burst)),
            RateLimitTier.EXECUTE: (execute_rate_per_min / 60.0, float(execute_burst)),
            RateLimitTier.METRICS: (metrics_rate_per_min / 60.0, float(metrics_burst)),
        }

        # Buckets: Dict[tier, Dict[client_id, (tokens, last_update)]]
        self._buckets: Dict[RateLimitTier, Dict[str, Tuple[float, float]]] = {
            tier: {} for tier in RateLimitTier
        }

        self._last_cleanup = time.time()

    def check(
        self,
        client_id: str,
        tier: RateLimitTier = RateLimitTier.READ,
        tokens_requested: float = 1.0,
    ) -> Tuple[bool, int, int]:
        """Checks if a request is permitted under the specified tier's token bucket.

        Args:
            client_id: Client identifier (IP address or API key ID).
            tier: RateLimitTier enum.
            tokens_requested: Number of tokens needed (default 1.0).

        Returns:
            Tuple of (is_allowed, retry_after_seconds, remaining_tokens_int).
        """
        now = time.time()
        fill_rate, max_tokens = self._tier_configs.get(
            tier, (120.0 / 60.0, 30.0)
        )

        with self._lock:
            self._maybe_cleanup(now)

            tier_buckets = self._buckets[tier]
            if client_id not in tier_buckets:
                if len(tier_buckets) >= self.max_clients:
                    # Drop oldest entry
                    first_key = next(iter(tier_buckets))
                    del tier_buckets[first_key]
                tier_buckets[client_id] = (max_tokens, now)

            current_tokens, last_time = tier_buckets[client_id]

            # Replenish tokens based on elapsed time
            elapsed = max(0.0, now - last_time)
            replenished = min(max_tokens, current_tokens + (elapsed * fill_rate))

            if replenished >= tokens_requested:
                new_tokens = replenished - tokens_requested
                tier_buckets[client_id] = (new_tokens, now)
                return True, 0, int(new_tokens)
            else:
                # Calculate wait time needed for 1 token
                deficit = tokens_requested - replenished
                retry_after = int(max(1.0, (deficit / fill_rate) + 0.99)) if fill_rate > 0 else 60
                tier_buckets[client_id] = (replenished, now)
                return False, retry_after, int(replenished)

    def reset(self) -> None:
        """Resets all token buckets (used in testing)."""
        with self._lock:
            for tier in RateLimitTier:
                self._buckets[tier].clear()

    def _maybe_cleanup(self, now: float) -> None:
        """Removes entries inactive for > 1 hour."""
        if now - self._last_cleanup < 300.0:
            return
        self._last_cleanup = now
        stale_threshold = now - 3600.0
        for tier in RateLimitTier:
            stale_keys = [
                k for k, (_, t) in self._buckets[tier].items() if t < stale_threshold
            ]
            for k in stale_keys:
                del self._buckets[tier][k]


# Global singleton rate limiter instance
rate_limiter = TieredTokenBucketRateLimiter()
