"""FastAPI authentication dependencies, scope verification, and security middleware."""

from typing import Callable, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from skyvanta.deployment.security.api_keys import APIKeyRecord, api_key_manager
from skyvanta.deployment.security.audit import security_audit_logger, SecurityEventType
from skyvanta.deployment.security.policies import Scope, has_scope
from skyvanta.deployment.security.redaction import mask_api_key

# HTTP Bearer security scheme for Swagger / OpenAPI documentation
http_bearer_scheme = HTTPBearer(auto_error=False)


def extract_api_key_from_request(request: Request) -> Optional[str]:
    """Extracts API key from Authorization header, X-API-Key header, or Sec-WebSocket-Protocol."""
    # 1. Check Authorization: Bearer <token>
    auth_header = request.headers.get("authorization")
    if auth_header:
        parts = auth_header.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        elif len(parts) == 1 and parts[0].startswith("sk_"):
            return parts[0]

    # 2. Check X-API-Key header
    x_api_key = request.headers.get("x-api-key")
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()

    return None


async def get_current_api_key(
    request: Request,
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer_scheme),
) -> APIKeyRecord:
    """Authenticates caller via API key header and records audit events."""
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    method = request.method

    # Extract raw key
    raw_key = auth_creds.credentials if auth_creds else extract_api_key_from_request(request)

    if not raw_key:
        security_audit_logger.record(
            event_type=SecurityEventType.AUTH_FAILURE,
            message="Missing API key in request",
            severity="WARNING",
            client_ip=client_ip,
            path=path,
            method=method,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    # Validate key constant-time
    record = api_key_manager.verify_key(raw_key)

    if record is None:
        security_audit_logger.record(
            event_type=SecurityEventType.AUTH_REJECTED,
            message=f"Rejected invalid, revoked, or expired API key ({mask_api_key(raw_key)})",
            severity="WARNING",
            client_ip=client_ip,
            path=path,
            method=method,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, revoked, or expired API key.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    # Record successful authentication
    security_audit_logger.record(
        event_type=SecurityEventType.AUTH_SUCCESS,
        message=f"API key '{record.name}' ({record.key_id}) authenticated successfully",
        severity="INFO",
        client_ip=client_ip,
        path=path,
        method=method,
        key_id=record.key_id,
        details={"scopes": [s.value for s in record.scopes]},
    )

    request.state.api_key = record
    return record


def require_scope(required_scope: Scope) -> Callable:
    """Creates a FastAPI dependency requiring the authenticated caller to have a specific scope."""

    async def _dependency(
        request: Request,
        key_record: APIKeyRecord = Depends(get_current_api_key),
    ) -> APIKeyRecord:
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        method = request.method

        if not has_scope(key_record.scopes, required_scope):
            security_audit_logger.record(
                event_type=SecurityEventType.FORBIDDEN,
                message=(
                    f"API key '{key_record.name}' ({key_record.key_id}) denied access: "
                    f"missing required '{required_scope.value}' scope"
                ),
                severity="WARNING",
                client_ip=client_ip,
                path=path,
                method=method,
                key_id=key_record.key_id,
                required_scope=required_scope.value,
                details={"granted_scopes": [s.value for s in key_record.scopes]},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Requires '{required_scope.value}' scope.",
            )

        return key_record

    return _dependency
