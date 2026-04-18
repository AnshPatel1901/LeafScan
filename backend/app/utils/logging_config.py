"""
Logging configuration — called once at application startup.
JSON-formatted in production; human-readable in development.
"""

import logging
import logging.config
import sys
from typing import Any

from app.core.config import settings


def configure_logging() -> None:
    """Configure root logger based on the current environment."""

    log_level = "DEBUG" if settings.DEBUG else "INFO"
    is_production = settings.ENVIRONMENT == "production"

    if is_production:
        fmt = (
            '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","message":"%(message)s"}'
        )
    else:
        fmt = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"

    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": fmt,
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
        "loggers": {
            # Quiet noisy third-party libs in production
            "uvicorn": {"level": "WARNING" if is_production else "INFO"},
            "uvicorn.error": {"level": "ERROR"},
            "uvicorn.access": {"level": "WARNING" if is_production else "INFO"},
            "sqlalchemy.engine": {
                "level": "DEBUG" if settings.DEBUG else "WARNING"
            },
            "httpx": {"level": "WARNING"},
        },
    }

    logging.config.dictConfig(config)
