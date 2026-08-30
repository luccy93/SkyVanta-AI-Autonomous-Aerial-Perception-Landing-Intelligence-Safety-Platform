"""Unit tests for API key generation, cryptographic hashing, and constant-time validation."""

import time
import pytest

from skyvanta.deployment.security.api_keys import (
    APIKeyManager,
    APIKeyRecord,
    hash_key_secret,
)
from skyvanta.deployment.security.policies import Scope


def test_api_key_generation_and_hashing():
    """1. Generated keys have secure format, store SHA-256 hash, and verify successfully."""
    manager = APIKeyManager()
    raw_key, record = manager.create_key(
        name="test_operator",
        scopes={Scope.READ, Scope.EXECUTE},
        prefix="sk_live",
    )

    assert raw_key.startswith("sk_live_")
    assert record.name == "test_operator"
    assert record.is_active is True
    assert record.is_expired is False
    assert Scope.READ in record.scopes
    assert Scope.EXECUTE in record.scopes
    assert record.key_hash == hash_key_secret(raw_key)

    # Verification succeeds
    verified = manager.verify_key(raw_key)
    assert verified is not None
    assert verified.key_id == record.key_id


def test_api_key_invalid_and_empty():
    """2. Non-existent, corrupted, or empty keys return None."""
    manager = APIKeyManager()
    assert manager.verify_key("") is None
    assert manager.verify_key("sk_live_invalid_key_123456789") is None
    assert manager.verify_key(None) is None  # type: ignore
    assert manager.verify_key("random_garbage_string") is None


def test_api_key_revocation():
    """3. Revoked API keys immediately fail verification."""
    manager = APIKeyManager()
    raw_key, record = manager.create_key(
        name="revocable_key",
        scopes={Scope.READ},
    )
    assert manager.verify_key(raw_key) is not None

    # Revoke key
    success = manager.revoke_key(record.key_id)
    assert success is True

    # Verification must now fail
    assert manager.verify_key(raw_key) is None
    assert manager.get_key(record.key_id).is_active is False


def test_api_key_expiration():
    """4. Expired keys fail verification after TTL has elapsed."""
    manager = APIKeyManager()
    # 0.1 second lifetime
    raw_key, record = manager.create_key(
        name="short_lived_key",
        scopes={Scope.READ},
        expires_in_sec=0.1,
    )
    assert manager.verify_key(raw_key) is not None
    assert record.is_expired is False

    # Sleep past expiration
    time.sleep(0.15)
    assert record.is_expired is True
    assert manager.verify_key(raw_key) is None


def test_api_key_listing_never_exposes_secrets():
    """5. Listing keys exposes only non-sensitive metadata (never raw keys or hashes)."""
    manager = APIKeyManager()
    raw_key, record = manager.create_key(
        name="audited_key",
        scopes={Scope.EXECUTE},
    )

    listing = manager.list_keys()
    assert isinstance(listing, list)
    target = next((item for item in listing if item["key_id"] == record.key_id), None)
    assert target is not None
    assert target["name"] == "audited_key"
    assert "scopes" in target
    assert "key_hash" not in target
    assert raw_key not in str(target)
