"""Performance benchmark measuring latency overhead of observability layer (D7-23)."""

import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from skyvanta.deployment.observability.middleware import ObservabilityMiddleware


def test_observability_latency_overhead():
    """ObservabilityMiddleware overhead must be minimal (< 2.0 ms per request)."""
    # 1. Baseline App without observability
    app_base = FastAPI()

    @app_base.get("/ping")
    def ping_base():
        return {"status": "ok"}

    client_base = TestClient(app_base)

    # Warmup
    for _ in range(20):
        client_base.get("/ping")

    t0 = time.perf_counter()
    n_iters = 100
    for _ in range(n_iters):
        resp = client_base.get("/ping")
        assert resp.status_code == 200
    baseline_total_ms = (time.perf_counter() - t0) * 1000.0
    baseline_avg_ms = baseline_total_ms / n_iters

    # 2. Instrumented App with ObservabilityMiddleware
    app_obs = FastAPI()
    app_obs.add_middleware(ObservabilityMiddleware, slow_request_threshold_ms=1000.0, environment="testing")

    @app_obs.get("/ping")
    def ping_obs():
        return {"status": "ok"}

    client_obs = TestClient(app_obs)

    # Warmup
    for _ in range(20):
        client_obs.get("/ping")

    t1 = time.perf_counter()
    for _ in range(n_iters):
        resp = client_obs.get("/ping")
        assert resp.status_code == 200
    obs_total_ms = (time.perf_counter() - t1) * 1000.0
    obs_avg_ms = obs_total_ms / n_iters

    overhead_ms = obs_avg_ms - baseline_avg_ms

    print(
        f"\n[D7-23 Performance Benchmark] Baseline: {baseline_avg_ms:.3f}ms/req | "
        f"Observability: {obs_avg_ms:.3f}ms/req | Overhead: {overhead_ms:.3f}ms/req"
    )

    # Assert overhead per request is under 2.0 ms
    assert overhead_ms < 2.0
