"""
Request/response logging middleware.

Logs every incoming request and its outcome with timing information.
Sensitive paths (e.g. /auth) are logged at a lower level.
"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_SENSITIVE_PATHS = {"/auth/login", "/auth/signup", "/auth/refresh-token"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logging with unique request IDs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        # Attach request_id for downstream logging
        request.state.request_id = request_id

        path = request.url.path
        is_sensitive = path in _SENSITIVE_PATHS

        logger.info(
            "[%s] → %s %s | client=%s",
            request_id,
            request.method,
            path if not is_sensitive else path + " [redacted]",
            request.client.host if request.client else "unknown",
        )

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "[%s] ← %s %s | status=%d | %.1fms",
            request_id,
            request.method,
            path,
            response.status_code,
            elapsed_ms,
        )

        # Propagate request ID to client for debugging
        response.headers["X-Request-ID"] = request_id
        return response
