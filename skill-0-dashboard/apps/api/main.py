"""
Skill-0 Governance Dashboard API

FastAPI application providing REST APIs for the governance dashboard.
"""

import os
import logging
import time
import sys
import uuid
from contextvars import ContextVar

import structlog
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware

from .routers import stats, skills, reviews, scans, audit

# Inline logging setup (dashboard is independent of core API logging)
from typing import Optional
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

def get_log_level() -> str:
    return os.getenv("SKILL0_LOG_LEVEL", "INFO").upper()

def add_request_id(logger, method_name: str, event_dict: dict) -> dict:
    rid = request_id_var.get()
    if rid:
        event_dict["request_id"] = rid
    return event_dict

def configure_logging() -> None:
    log_format = os.environ.get("SKILL0_LOG_FORMAT", "json")
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
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

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
    root_logger.setLevel(get_log_level())

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

def generate_request_id() -> str:
    return uuid.uuid4().hex[:12]

logger: structlog.BoundLogger
configure_logging()
logger = structlog.get_logger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = generate_request_id()
        token = request_id_var.set(rid)

        bound_logger = logger.bind(request_id=rid, method=request.method, path=request.url.path)
        bound_logger.info("request_started")

        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        response.headers["X-Request-ID"] = rid
        bound_logger.info("request_completed", status=response.status_code, duration_ms=duration_ms)

        request_id_var.reset(token)
        return response

app = FastAPI(
    title="Skill-0 Governance Dashboard API",
    description="REST API for the Skill-0 governance dashboard providing security scanning, equivalence testing, and approval workflow management.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS origins from environment variable
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware (structured logging with per-request IDs)
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(stats.router, prefix="/api", tags=["Stats"])
app.include_router(skills.router, prefix="/api", tags=["Skills"])
app.include_router(reviews.router, prefix="/api", tags=["Reviews"])
app.include_router(scans.router, prefix="/api", tags=["Scans"])
app.include_router(audit.router, prefix="/api", tags=["Audit"])


@app.get("/")
async def root():
    return {
        "name": "Skill-0 Governance API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
