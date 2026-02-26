"""
Skill-0 Governance Dashboard API

FastAPI application providing REST APIs for the governance dashboard.
"""

import os

from fastapi import Depends, FastAPI
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
