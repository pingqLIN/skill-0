"""
Skill-0 Governance Dashboard API

FastAPI application providing REST APIs for the governance dashboard.
"""

import logging
import os
import sys
import time
import uuid

import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .auth import require_auth
from .routers import stats, skills, reviews, scans, audit

# CORS origins from environment variable
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")

app = FastAPI(
    title="Skill-0 Governance Dashboard API",
    description="REST API for the Skill-0 governance dashboard providing security scanning, equivalence testing, and approval workflow management.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS — controlled by CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured logging setup
def _setup_dashboard_logging():
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.UnicodeDecoder(),
    ]
    log_format = os.getenv("SKILL0_LOG_FORMAT", "json").lower()
    if log_format == "json":
        renderer = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, renderer],
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


_setup_dashboard_logging()
_logger = structlog.get_logger("dashboard")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Add request ID and structured logging to every request."""
    rid = uuid.uuid4().hex[:8]
    structlog.contextvars.bind_contextvars(request_id=rid)
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 2)
    _logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
    )
    response.headers["X-Request-ID"] = rid
    structlog.contextvars.unbind_contextvars("request_id")
    return response


# Auth dependency applied to all /api/* routes
_auth_deps = [Depends(require_auth)]

# Include routers
app.include_router(stats.router, prefix="/api", tags=["Stats"], dependencies=_auth_deps)
app.include_router(skills.router, prefix="/api", tags=["Skills"], dependencies=_auth_deps)
app.include_router(reviews.router, prefix="/api", tags=["Reviews"], dependencies=_auth_deps)
app.include_router(scans.router, prefix="/api", tags=["Scans"], dependencies=_auth_deps)
app.include_router(audit.router, prefix="/api", tags=["Audit"], dependencies=_auth_deps)


@app.get("/")
async def root():
    """API root - returns basic API information"""
    return {
        "name": "Skill-0 Governance API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}
