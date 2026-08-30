"""Credential scrubbing, API key masking, and diagnostic security redaction."""

import re
from typing import Any, Dict, List, Union

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|passwd|secret|token|auth|authorization|cookie|set-cookie|api[_-]?key|credential|private[_-]?key)",
    re.IGNORECASE,
)

_BEARER_PATTERN = re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE)
_API_KEY_PATTERN = re.compile(r"sk_(live|test)_[a-zA-Z0-9_\-]+", re.IGNORECASE)


def mask_api_key(key: str) -> str:
    """Returns a safe masked representation of an API key for audit logs."""
    if not key or not isinstance(key, str):
        return "[REDACTED]"
    clean_key = key.strip()
    if len(clean_key) <= 12:
        return "[REDACTED]"
    prefix = clean_key[:8]
    suffix = clean_key[-4:]
    return f"{prefix}...{suffix}"


def sanitize_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    """Strips credentials, cookies, and tokens from request or response headers."""
    sanitized = {}
    for k, v in headers.items():
        str_k = str(k)
        if _SENSITIVE_KEY_PATTERN.search(str_k):
            sanitized[str_k] = "[REDACTED]"
        else:
            sanitized[str_k] = sanitize_payload(v)
    return sanitized


def sanitize_payload(data: Any) -> Any:
    """Recursively redacts secrets and credentials from data payloads."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            str_key = str(k)
            if _SENSITIVE_KEY_PATTERN.search(str_key):
                sanitized[str_key] = "[REDACTED]"
            else:
                sanitized[str_key] = sanitize_payload(v)
        return sanitized
    elif isinstance(data, (list, tuple)):
        cleaned = [sanitize_payload(item) for item in data]
        return type(data)(cleaned)
    elif isinstance(data, str):
        masked = _BEARER_PATTERN.sub("Bearer [REDACTED]", data)
        masked = _API_KEY_PATTERN.sub("sk_\\1_[REDACTED]", masked)
        return masked
    else:
        return data
