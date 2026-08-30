"""WebSocket handshake authentication and connection admission security."""

from typing import Optional
from fastapi import WebSocket, status

from skyvanta.deployment.security.api_keys import APIKeyRecord, api_key_manager
from skyvanta.deployment.security.audit import security_audit_logger, SecurityEventType
from skyvanta.deployment.security.policies import Scope, has_scope
from skyvanta.deployment.security.redaction import mask_api_key


def extract_websocket_token(websocket: WebSocket) -> Optional[str]:
    """Extracts authentication token from WebSocket handshake headers or protocols."""
    # 1. Authorization: Bearer <key>
    auth = websocket.headers.get("authorization")
    if auth:
        parts = auth.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        elif len(parts) == 1 and parts[0].startswith("sk_"):
            return parts[0]

    # 2. X-API-Key header
    x_key = websocket.headers.get("x-api-key")
    if x_key and x_key.strip():
        return x_key.strip()

    # 3. Sec-WebSocket-Protocol (e.g. 'skyvanta-v1, bearer.sk_live_...')
    sec_proto = websocket.headers.get("sec-websocket-protocol")
    if sec_proto:
        for item in sec_proto.split(","):
            subproto = item.strip()
            if subproto.startswith("bearer."):
                return subproto[7:]
            elif subproto.startswith("sk_"):
                return subproto

    return None


async def authenticate_websocket(
    websocket: WebSocket,
    required_scope: Scope = Scope.READ,
) -> Optional[APIKeyRecord]:
    """Validates WebSocket client credentials during connection establishment.

    Returns:
        APIKeyRecord if caller is authenticated and authorized; None otherwise (closes connection with 1008).
    """
    client_ip = websocket.client.host if websocket.client else "unknown"
    path = websocket.url.path

    raw_token = extract_websocket_token(websocket)

    if not raw_token:
        security_audit_logger.record(
            event_type=SecurityEventType.WEBSOCKET_AUTH_FAILURE,
            message="WebSocket handshake rejected: missing credentials",
            severity="WARNING",
            client_ip=client_ip,
            path=path,
            method="WS",
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing API key")
        return None

    record = api_key_manager.verify_key(raw_token)

    if record is None:
        security_audit_logger.record(
            event_type=SecurityEventType.WEBSOCKET_AUTH_FAILURE,
            message=f"WebSocket handshake rejected: invalid/revoked key ({mask_api_key(raw_token)})",
            severity="WARNING",
            client_ip=client_ip,
            path=path,
            method="WS",
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid API key")
        return None

    if not has_scope(record.scopes, required_scope):
        security_audit_logger.record(
            event_type=SecurityEventType.WEBSOCKET_AUTH_FAILURE,
            message=f"WebSocket connection rejected: key '{record.name}' lacks '{required_scope.value}' scope",
            severity="WARNING",
            client_ip=client_ip,
            path=path,
            method="WS",
            key_id=record.key_id,
            required_scope=required_scope.value,
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Insufficient permissions")
        return None

    security_audit_logger.record(
        event_type=SecurityEventType.AUTH_SUCCESS,
        message=f"WebSocket client '{record.name}' ({record.key_id}) connected with scope '{required_scope.value}'",
        severity="INFO",
        client_ip=client_ip,
        path=path,
        method="WS",
        key_id=record.key_id,
    )

    return record
