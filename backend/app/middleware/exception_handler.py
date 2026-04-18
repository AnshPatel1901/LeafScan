"""
Global exception handler middleware.

Catches domain exceptions and converts them to the standard API envelope so
every error response is consistent — no raw tracebacks reach the client.
"""

from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def _error_body(message: str, detail=None) -> dict:
    return {"success": False, "data": detail, "message": message}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to *app*."""

    # ── Domain exceptions ─────────────────────────────────────────────────────

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        logger.warning(
            "AppException [%s %s]: %s",
            request.method,
            request.url.path,
            exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.message, exc.detail),
        )

    # ── Pydantic validation errors ────────────────────────────────────────────

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Format Pydantic errors into a readable list
        errors = [
            {
                "field": " → ".join(str(loc) for loc in err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        logger.info(
            "Validation error [%s %s]: %s",
            request.method,
            request.url.path,
            errors,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body("Request validation failed", errors),
        )

    # ── Generic / unhandled exceptions ────────────────────────────────────────

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled exception [%s %s]:\n%s",
            request.method,
            request.url.path,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "An unexpected internal error occurred. "
                "Please try again later."
            ),
        )
