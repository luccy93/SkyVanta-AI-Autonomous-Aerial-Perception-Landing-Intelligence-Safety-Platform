"""Request body and header payload size limiter middleware."""

import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from skyvanta.deployment.security.audit import security_audit_logger, SecurityEventType


class PayloadLimitMiddleware(BaseHTTPMiddleware):
    """Rejects oversized request bodies and headers to prevent resource exhaustion attacks."""

    def __init__(
        self,
        app,
        max_body_bytes: int = 65536,       # 64 KB default for JSON payloads
        max_header_bytes: int = 16384,     # 16 KB default for headers
    ):
        super().__init__(app)
        self.max_body_bytes = max_body_bytes
        self.max_header_bytes = max_header_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        # 1. Header size check
        total_header_bytes = sum(
            (len(k) if isinstance(k, bytes) else len(str(k).encode("utf-8")))
            + (len(v) if isinstance(v, bytes) else len(str(v).encode("utf-8")))
            for k, v in request.headers.raw
        )
        if total_header_bytes > self.max_header_bytes:
            security_audit_logger.record(
                event_type=SecurityEventType.INVALID_REQUEST,
                message=f"Request headers size ({total_header_bytes} bytes) exceeds limit ({self.max_header_bytes} bytes)",
                severity="WARNING",
                client_ip=client_ip,
                path=request.url.path,
                method=request.method,
                details={"header_bytes": total_header_bytes, "max_allowed": self.max_header_bytes},
            )
            return JSONResponse(
                status_code=431,  # Request Header Fields Too Large
                content={"detail": "Request headers exceed maximum allowable size."},
            )

        # 2. Content-Length check for requests with body
        content_length_header = request.headers.get("content-length")
        if content_length_header is not None:
            try:
                content_length = int(content_length_header)
                if content_length > self.max_body_bytes:
                    security_audit_logger.record(
                        event_type=SecurityEventType.INVALID_REQUEST,
                        message=f"Request body size ({content_length} bytes) exceeds limit ({self.max_body_bytes} bytes)",
                        severity="WARNING",
                        client_ip=client_ip,
                        path=request.url.path,
                        method=request.method,
                        details={"content_length": content_length, "max_allowed": self.max_body_bytes},
                    )
                    return JSONResponse(
                        status_code=413,  # Payload Too Large / Content Too Large
                        content={
                            "detail": f"Request payload ({content_length} bytes) exceeds maximum allowable limit of {self.max_body_bytes} bytes."
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)
