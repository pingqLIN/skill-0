"""
Structured logging configuration for Skill-0 API

Uses structlog for JSON-formatted structured logging with request context.
"""

import logging
import os
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

import structlog

# Context variable for request-scoped data
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def get_log_level() -> str:
    """Get log level from environment, default INFO"""
    return os.getenv("SKILL0_LOG_LEVEL", "INFO").upper()


def add_request_id(
    logger: logging.Logger, method_name: str, event_dict: dict
) -> dict:
    """Add request_id from context var if available"""
    rid = request_id_var.get()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging() -> None:
    """Configure structlog with JSON output for production, console for dev"""
    log_format = os.getenv("SKILL0_LOG_FORMAT", "json")  # json or console

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if log_format == "console":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ]
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, get_log_level(), logging.INFO))

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def generate_request_id() -> str:
    """Generate a short request ID"""
    return uuid.uuid4().hex[:12]


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger bound with the given name"""
    return structlog.get_logger(name)
