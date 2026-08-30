"""Observability, slow request detection, and lightweight API rate-limiting middleware."""

import collections
import time
from typing import Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from skyvanta.deployment.observability.events import EventType, event_logger, redact_sensitive_data
from skyvanta.deployment.observability.metrics import RouteNormalizer, metrics_collector


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Measures request latency, registers bounded metrics, and flags slow requests."""

    def __init__(self, app, slow_request_threshold_ms: float = 1000.0, environment: str = "production"):
        super().__init__(app)
        self.slow_request_threshold_ms = float(slow_request_threshold_ms)
        self.environment = environment

    async def dispatch(self, request: Request, call_next) -> Response:
        t_start = time.perf_counter()
        method = request.method
        raw_path = request.url.path
        norm_route = RouteNormalizer.normalize(raw_path)
        req_id = getattr(request.state, "request_id", request.headers.get("X-Request-ID", "unknown"))

        try:
            response: Response = await call_next(request)
            duration_ms = (time.perf_counter() - t_start) * 1000.0
            status_code = response.status_code
            is_slow = duration_ms >= self.slow_request_threshold_ms

            # 1. Flag slow requests
            if is_slow:
                event_logger.emit(
                    event_type=EventType.SLOW_REQUEST,
                    message=f"Slow HTTP request on {method} {norm_route} ({round(duration_ms, 2)} ms)",
                    severity="WARNING",
                    details={
                        "method": method,
                        "route": norm_route,
                        "status_code": status_code,
                        "duration_ms": round(duration_ms, 2),
                        "threshold_ms": self.slow_request_threshold_ms,
                        "request_id": req_id,
                    },
                    environment=self.environment,
                )

            # 2. Record in metrics collector
            metrics_collector.record_http_request(
                method=method,
                path=raw_path,
                status_code=status_code,
                duration_ms=round(duration_ms, 3),
                is_slow=is_slow,
            )

            # Attach response timing header
            response.headers["X-Response-Time-Ms"] = str(round(duration_ms, 2))
            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - t_start) * 1000.0
            metrics_collector.record_http_request(
                method=method,
                path=raw_path,
                status_code=500,
                duration_ms=round(duration_ms, 3),
                is_slow=(duration_ms >= self.slow_request_threshold_ms),
            )
            metrics_collector.record_error("internal")

            event_logger.emit(
                event_type=EventType.REQUEST_ERROR,
                message=f"Unhandled error in HTTP {method} {norm_route}: {str(exc)}",
                severity="ERROR",
                details={
                    "method": method,
                    "route": norm_route,
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                    "request_id": req_id,
                },
                environment=self.environment,
            )
            raise


class TokenBucketRateLimiter:
    """Bounded, thread-safe token bucket rate limiter per client IP."""

    def __init__(self, requests_per_minute: int = 120, burst_capacity: int = 30, max_clients: int = 2000):
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.capacity = burst_capacity
        self.max_clients = max_clients
        # Key: client_ip -> (tokens, last_update_sec)
        self._buckets: Dict[str, Tuple[float, float]] = collections.OrderedDict()

    def allow_request(self, client_ip: str) -> bool:
        """Determines if a request is permitted under rate limit thresholds."""
        now = time.monotonic()
        
        # Evict oldest if capacity exceeded
        if len(self._buckets) > self.max_clients:
            self._buckets.pop(next(iter(self._buckets)), None)

        if client_ip not in self._buckets:
            self._buckets[client_ip] = (self.capacity - 1.0, now)
            return True

        tokens, last_time = self._buckets[client_ip]
        elapsed = now - last_time
        tokens = min(float(self.capacity), tokens + (elapsed * self.rate))

        if tokens >= 1.0:
            self._buckets[client_ip] = (tokens - 1.0, now)
            return True
        else:
            self._buckets[client_ip] = (tokens, now)
            return False


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Protects REST API endpoints against accidental request flooding."""

    def __init__(
        self,
        app,
        enabled: bool = True,
        requests_per_minute: int = 120,
        burst_capacity: int = 30,
        environment: str = "production",
    ):
        super().__init__(app)
        self.enabled = enabled
        self.limiter = TokenBucketRateLimiter(
            requests_per_minute=requests_per_minute,
            burst_capacity=burst_capacity,
        )
        self.environment = environment

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Bypass rate limiting for WebSocket handshakes & health checks
        raw_path = request.url.path
        if raw_path.startswith("/api/v1/telemetry/ws") or raw_path in ("/health", "/ready"):
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        if not self.limiter.allow_request(client_host):
            req_id = getattr(request.state, "request_id", request.headers.get("X-Request-ID", "unknown"))
            event_logger.emit(
                event_type=EventType.RATE_LIMIT_EXCEEDED,
                message=f"Rate limit exceeded for client {client_host} on {request.url.path}",
                severity="WARNING",
                details={
                    "client_ip": client_host,
                    "path": RouteNormalizer.normalize(raw_path),
                    "request_id": req_id,
                },
                environment=self.environment,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please slow down and retry shortly.",
                    "request_id": req_id,
                },
                headers={
                    "Retry-After": "5",
                    "X-Request-ID": req_id,
                },
            )

        return await call_next(request)
