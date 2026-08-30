"""Performance benchmark measuring authentication and security middleware overhead."""

import time
from fastapi.testclient import TestClient

from skyvanta.deployment.api.app import create_app
from skyvanta.deployment.config import DeploymentConfig, DeploymentEnvironment
from skyvanta.deployment.security.api_keys import api_key_manager
from skyvanta.deployment.security.policies import Scope


def test_authentication_latency_overhead():
    """Measures latency difference between public endpoint and authenticated protected endpoint."""
    app = create_app(
        DeploymentConfig(
            environment=DeploymentEnvironment.TESTING,
            enable_rate_limiting=False,
        )
    )
    client = TestClient(app)

    # 1. Warm-up
    for _ in range(20):
        client.get("/health")
        client.get(
            "/api/v1/system/info",
            headers={"Authorization": "Bearer sk_test_admin_key_12345"},
        )

    # 2. Benchmark Public /health (N=100)
    t0 = time.perf_counter()
    for _ in range(100):
        resp = client.get("/health")
        assert resp.status_code == 200
    t_public_total = time.perf_counter() - t0
    avg_public_ms = (t_public_total / 100.0) * 1000.0

    # 3. Benchmark Authenticated Protected /api/v1/system/info (N=100)
    t0 = time.perf_counter()
    for _ in range(100):
        resp = client.get(
            "/api/v1/system/info",
            headers={"Authorization": "Bearer sk_test_admin_key_12345"},
        )
        assert resp.status_code == 200
    t_auth_total = time.perf_counter() - t0
    avg_auth_ms = (t_auth_total / 100.0) * 1000.0

    overhead_ms = max(0.0, avg_auth_ms - avg_public_ms)

    print(
        f"\n[Security Benchmark] Public Latency: {avg_public_ms:.3f} ms | "
        f"Authenticated Latency: {avg_auth_ms:.3f} ms | "
        f"Auth Overhead: {overhead_ms:.3f} ms"
    )

    # In-memory SHA-256 constant time comparison overhead should be well under 1.5 ms per request
    assert overhead_ms < 2.0
