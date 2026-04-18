"""
Application entry point.

Creates and configures the FastAPI application:
    • Registers all middleware
    • Mounts API routers
    • Attaches exception handlers
    • Manages lifespan events (startup / shutdown)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.middleware.exception_handler import register_exception_handlers
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.utils.logging_config import configure_logging

# Configure logging before anything else
configure_logging()

logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    # Ensure upload directory exists
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory ready: %s", settings.UPLOAD_DIR)

    logger.info("Application startup complete — ready to serve requests")
    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Application shutting down...")
    from app.db.session import get_engine
    await get_engine().dispose()
    logger.info("Database connections closed")


# ── Application factory ───────────────────────────────────────────────────────


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-powered crop disease detection API. "
            "Upload plant images to get disease predictions and treatment advice."
        ),
        docs_url="/docs" if not settings.ENVIRONMENT == "production" else None,
        redoc_url="/redoc" if not settings.ENVIRONMENT == "production" else None,
        openapi_url="/openapi.json" if not settings.ENVIRONMENT == "production" else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Origins are controlled by CORS_ORIGINS env var (comma-separated).
    # In debug mode "*" is added so any local dev origin is accepted.
    origins = settings.cors_origins_list
    if settings.DEBUG and "*" not in origins:
        origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom middleware (outermost = last in chain) ──────────────────────────
    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()


# ── Dev entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        workers=1 if settings.DEBUG else 4,
    )
