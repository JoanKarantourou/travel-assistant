"""Structured logging configuration using structlog.

Configures structlog with either a human-readable console renderer (development)
or a JSON renderer (production), and bridges stdlib logging through the same pipeline.
"""

import logging
import sys
import uuid

import structlog

from travel_assistant.config import get_settings


def configure_logging() -> None:
    """Set up structlog and stdlib logging based on the current environment settings."""
    settings = get_settings()
    is_dev = settings.app.environment == "development"

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer = structlog.dev.ConsoleRenderer() if is_dev else structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging so third-party libraries go through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.app.log_level.upper(), logging.INFO),
    )


def bind_request_id() -> str:
    """Generate a fresh request ID, bind it to the structlog context, and return it."""
    request_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=request_id)
    return request_id


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Return a structlog bound logger for the given module name."""
    return structlog.get_logger(name)
