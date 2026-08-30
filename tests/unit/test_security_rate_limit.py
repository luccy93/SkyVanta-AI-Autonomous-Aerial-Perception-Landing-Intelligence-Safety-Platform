"""Unit tests for tiered token-bucket rate limiting and burst protection."""

import time
from skyvanta.deployment.security.rate_limit import (
    RateLimitTier,
    TieredTokenBucketRateLimiter,
)


def test_tiered_rate_limiter_burst_and_exhaustion():
    """1. Tiered rate limiter permits burst up to limit, then rejects until replenished."""
    limiter = TieredTokenBucketRateLimiter(
        read_rate_per_min=60,   # 1 token/sec
        read_burst=5,           # 5 burst tokens
        execute_rate_per_min=12,# 0.2 tokens/sec
        execute_burst=2,        # 2 burst tokens
    )

    client_id = "192.168.1.100"

    # Consume all 5 read tokens
    for i in range(5):
        allowed, retry_after, remaining = limiter.check(client_id, tier=RateLimitTier.READ)
        assert allowed is True
        assert remaining == 4 - i

    # 6th request must be rejected
    allowed, retry_after, remaining = limiter.check(client_id, tier=RateLimitTier.READ)
    assert allowed is False
    assert retry_after >= 1

    # Execute tier should have its own independent bucket
    allowed_exec, _, remaining_exec = limiter.check(client_id, tier=RateLimitTier.EXECUTE)
    assert allowed_exec is True
    assert remaining_exec == 1


def test_rate_limiter_replenishment():
    """2. Tokens replenish over time according to configured fill rate."""
    limiter = TieredTokenBucketRateLimiter(
        read_rate_per_min=600,  # 10 tokens/sec
        read_burst=2,
    )
    client_id = "10.0.0.1"

    # Exhaust burst
    limiter.check(client_id, tier=RateLimitTier.READ)
    limiter.check(client_id, tier=RateLimitTier.READ)
    allowed, _, _ = limiter.check(client_id, tier=RateLimitTier.READ)
    assert allowed is False

    # Wait 0.25 seconds (should replenish ~2.5 tokens)
    time.sleep(0.25)
    allowed, _, remaining = limiter.check(client_id, tier=RateLimitTier.READ)
    assert allowed is True
    assert remaining >= 0


def test_rate_limiter_separate_clients_isolation():
    """3. Different client IPs do not impact each other's rate limit buckets."""
    limiter = TieredTokenBucketRateLimiter(
        read_rate_per_min=60,
        read_burst=1,
    )

    # Client A consumes bucket
    limiter.check("client_a", tier=RateLimitTier.READ)
    allowed_a, _, _ = limiter.check("client_a", tier=RateLimitTier.READ)
    assert allowed_a is False

    # Client B should still have full bucket
    allowed_b, _, _ = limiter.check("client_b", tier=RateLimitTier.READ)
    assert allowed_b is True
