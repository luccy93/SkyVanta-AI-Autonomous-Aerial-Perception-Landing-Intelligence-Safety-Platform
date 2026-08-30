"""Unit tests for ObservabilityMiddleware and RateLimitingMiddleware."""

import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from skyvanta.deployment.observability.events import EventType, event_logger
from skyvanta.deployment.observability.metrics import metrics_collector
from skyvanta.deployment.observability.middleware import ObservabilityMiddleware, RateLimitingMiddleware, TokenBucketRateLimiter


def test_observability_middleware_timing_and_metrics():
    """ObservabilityMiddleware must attach response timing headers and record metrics."""
    metrics_collector.reset()
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware, slow_request_threshold_ms=500.0, environment="testing")

    @app.get("/test-endpoint")
    def sample_endpoint():
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/test-endpoint")

    assert response.status_code == 200
    assert "X-Response-Time-Ms" in response.headers
    assert float(response.headers["X-Response-Time-Ms"]) >= 0.0

    metrics = metrics_collector.get_http_metrics()
    assert metrics["total_requests"] == 1
    assert metrics["successful_requests"] == 1
    assert metrics["requests_by_status"][200] == 1


def test_observability_middleware_slow_request_detection():
    """ObservabilityMiddleware must emit SLOW_REQUEST event when threshold is exceeded."""
    event_logger.clear()
    app = FastAPI()
    # Set tiny 5ms threshold to test slow request detection
    app.add_middleware(ObservabilityMiddleware, slow_request_threshold_ms=5.0, environment="testing")

    @app.get("/slow-endpoint")
    def slow_endpoint():
        time.sleep(0.02)  # 20ms sleep > 5ms threshold
        return {"status": "slow"}

    client = TestClient(app)
    response = client.get("/slow-endpoint")
    assert response.status_code == 200

    events = event_logger.get_recent_events(limit=10)
    slow_events = [e for e in events if e["event_type"] == EventType.SLOW_REQUEST.value]
    assert len(slow_events) >= 1
    assert slow_events[0]["details"]["threshold_ms"] == 5.0


def test_rate_limiting_token_bucket():
    """TokenBucketRateLimiter must reject excessive bursts."""
    limiter = TokenBucketRateLimiter(requests_per_minute=60, burst_capacity=5)
    client_ip = "192.168.1.100"

    # First 5 requests should pass burst capacity
    for _ in range(5):
        assert limiter.allow_request(client_ip) is True

    # 6th request immediately after should be rate limited
    assert limiter.allow_request(client_ip) is False


def test_rate_limiting_middleware_429():
    """RateLimitingMiddleware must return 429 when client exceeds burst rate."""
    app = FastAPI()
    app.add_middleware(
        RateLimitingMiddleware,
        enabled=True,
        requests_per_minute=60,
        burst_capacity=3,
        environment="testing",
    )

    @app.get("/api/v1/data")
    def data_route():
        return {"data": 123}

    @app.get("/health")
    def health_route():
        return {"status": "healthy"}

    client = TestClient(app)

    # 3 allowed requests
    assert client.get("/api/v1/data").status_code == 200
    assert client.get("/api/v1/data").status_code == 200
    assert client.get("/api/v1/data").status_code == 200

    # 4th request must be 429
    resp_429 = client.get("/api/v1/data")
    assert resp_429.status_code == 429
    data = resp_429.json()
    assert data["error"] == "rate_limit_exceeded"
    assert "Retry-After" in resp_429.headers

    # /health route must NOT be rate limited
    assert client.get("/health").status_code == 200
