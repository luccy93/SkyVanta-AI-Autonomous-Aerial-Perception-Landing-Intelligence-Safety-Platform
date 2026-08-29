"""Request correlation ID and HTTP security headers middleware."""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique X-Request-ID into request state and outgoing response headers."""

    async def dispatch(self, request: Request, call_next):
        # Use existing incoming request ID or generate a new UUID4
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = uuid.uuid4().hex

        # Attach to request state for access in route handlers and logging
        request.state.request_id = request_id

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attaches standard defensive HTTP security headers to outgoing responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Standard defensive headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response
