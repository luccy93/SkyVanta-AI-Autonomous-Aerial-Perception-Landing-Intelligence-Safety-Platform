"""API key lifecycle, cryptographic SHA-256 hashing, and constant-time verification."""

from dataclasses import dataclass, field
import hashlib
import hmac
import os
import secrets
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from skyvanta.deployment.security.policies import Scope


def hash_key_secret(key_str: str) -> str:
    """Computes a cryptographic SHA-256 digest of the raw API key."""
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()


@dataclass
class APIKeyRecord:
    """Non-sensitive metadata and secure hash representation of an API key."""

    key_id: str
    name: str
    key_hash: str
    scopes: Set[Scope] = field(default_factory=set)
    is_active: bool = True
    expires_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)

    @property
    def is_expired(self) -> bool:
        """Returns True if the key has expired."""
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at


class APIKeyManager:
    """Thread-safe API key registry and constant-time authentication validator."""

    def __init__(self):
        self._lock = threading.RLock()
        # Key: key_id -> APIKeyRecord
        self._keys: Dict[str, APIKeyRecord] = {}
        # Secondary index: key_hash -> key_id for O(1) lookup
        self._hash_to_id: Dict[str, str] = {}
        self._load_from_env()

    def create_key(
        self,
        name: str,
        scopes: Set[Scope],
        prefix: str = "sk_live",
        expires_in_sec: Optional[float] = None,
    ) -> Tuple[str, APIKeyRecord]:
        """Generates a new cryptographically secure API key and records its hash.

        Args:
            name: Human-readable identifier for the key (e.g. 'flight_operator_1').
            scopes: Set of authorized Scope enums.
            prefix: Key prefix ('sk_live' or 'sk_test').
            expires_in_sec: Optional lifetime in seconds.

        Returns:
            Tuple of (raw_plaintext_key, APIKeyRecord).
            WARNING: raw_plaintext_key is returned ONLY once upon creation.
        """
        key_id = uuid4().hex[:10]
        secret_part = secrets.token_urlsafe(32)
        raw_key = f"{prefix}_{key_id}_{secret_part}"
        key_hash = hash_key_secret(raw_key)
        now = time.time()
        expires_at = (now + expires_in_sec) if expires_in_sec else None

        record = APIKeyRecord(
            key_id=key_id,
            name=name,
            key_hash=key_hash,
            scopes=set(scopes),
            is_active=True,
            expires_at=expires_at,
            created_at=now,
        )

        with self._lock:
            self._keys[key_id] = record
            self._hash_to_id[key_hash] = key_id

        return raw_key, record

    def register_raw_key(
        self,
        raw_key: str,
        name: str,
        scopes: Set[Scope],
        is_active: bool = True,
        expires_at: Optional[float] = None,
    ) -> APIKeyRecord:
        """Registers a known raw key (e.g. from environment configuration) by storing its hash."""
        clean_key = raw_key.strip()
        key_hash = hash_key_secret(clean_key)
        key_id = f"id_{uuid4().hex[:10]}"

        record = APIKeyRecord(
            key_id=key_id,
            name=name,
            key_hash=key_hash,
            scopes=set(scopes),
            is_active=is_active,
            expires_at=expires_at,
            created_at=time.time(),
        )

        with self._lock:
            self._keys[key_id] = record
            self._hash_to_id[key_hash] = key_id

        return record

    def verify_key(self, raw_key: str) -> Optional[APIKeyRecord]:
        """Validates a raw API key using constant-time comparison.

        Returns:
            APIKeyRecord if the key is valid, active, and unexpired; None otherwise.
        """
        if not raw_key or not isinstance(raw_key, str):
            return None

        clean_key = raw_key.strip()
        computed_hash = hash_key_secret(clean_key)

        with self._lock:
            # 1. Lookup candidate record by hash index
            key_id = self._hash_to_id.get(computed_hash)
            if not key_id or key_id not in self._keys:
                # Perform a dummy constant-time comparison against fixed string to prevent timing leaks
                _ = hmac.compare_digest(computed_hash, "0" * 64)
                return None

            record = self._keys[key_id]

            # 2. Constant-time digest comparison
            if not hmac.compare_digest(computed_hash, record.key_hash):
                return None

            # 3. Status and Expiration Checks
            if not record.is_active or record.is_expired:
                return None

            return record

    def revoke_key(self, key_id: str) -> bool:
        """Revokes an API key by marking it inactive."""
        with self._lock:
            if key_id in self._keys:
                self._keys[key_id].is_active = False
                return True
            return False

    def get_key(self, key_id: str) -> Optional[APIKeyRecord]:
        """Retrieves non-sensitive metadata for a key ID."""
        with self._lock:
            return self._keys.get(key_id)

    def list_keys(self) -> List[Dict[str, Any]]:
        """Returns non-sensitive metadata for all registered keys."""
        with self._lock:
            return [
                {
                    "key_id": r.key_id,
                    "name": r.name,
                    "scopes": [s.value for s in r.scopes],
                    "is_active": r.is_active,
                    "is_expired": r.is_expired,
                    "created_at": r.created_at,
                    "expires_at": r.expires_at,
                }
                for r in self._keys.values()
            ]

    def clear(self) -> None:
        """Clears all registered keys (used in test setup)."""
        with self._lock:
            self._keys.clear()
            self._hash_to_id.clear()

    def _load_from_env(self) -> None:
        """Initializes API keys from environment configuration."""
        admin_key = os.getenv("SKYVANTA_ADMIN_KEY")
        if admin_key and admin_key.strip():
            self.register_raw_key(admin_key, name="env_admin", scopes={Scope.ADMIN})

        exec_key = os.getenv("SKYVANTA_EXECUTE_KEY")
        if exec_key and exec_key.strip():
            self.register_raw_key(exec_key, name="env_execute", scopes={Scope.EXECUTE})

        read_key = os.getenv("SKYVANTA_READ_KEY")
        if read_key and read_key.strip():
            self.register_raw_key(read_key, name="env_read", scopes={Scope.READ})

        # Comma-separated complex format: key:name:scope1+scope2
        keys_csv = os.getenv("SKYVANTA_API_KEYS", "")
        if keys_csv.strip():
            for item in keys_csv.split(","):
                parts = item.strip().split(":")
                if len(parts) >= 3:
                    k_str, name_str, scopes_str = parts[0], parts[1], parts[2]
                    parsed_scopes = set()
                    for s in scopes_str.split("+"):
                        try:
                            parsed_scopes.add(Scope(s.strip().lower()))
                        except ValueError:
                            pass
                    if parsed_scopes:
                        self.register_raw_key(k_str, name=name_str, scopes=parsed_scopes)

        # Standard testing / development baseline keys
        self.register_raw_key("sk_test_admin_key_12345", name="default_test_admin", scopes={Scope.ADMIN})
        self.register_raw_key("sk_test_exec_key_12345", name="default_test_exec", scopes={Scope.EXECUTE})
        self.register_raw_key("sk_test_read_key_12345", name="default_test_read", scopes={Scope.READ})


# Global singleton instance
api_key_manager = APIKeyManager()
