<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""
Skill-0 Governance Dashboard API

FastAPI application providing REST APIs for the governance dashboard.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import stats, skills, reviews, scans, audit

app = FastAPI(
    title="Skill-0 Governance Dashboard API",
    description="REST API for the Skill-0 governance dashboard providing security scanning, equivalence testing, and approval workflow management.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stats.router, prefix="/api", tags=["Stats"])
app.include_router(skills.router, prefix="/api", tags=["Skills"])
app.include_router(reviews.router, prefix="/api", tags=["Reviews"])
app.include_router(scans.router, prefix="/api", tags=["Scans"])
app.include_router(audit.router, prefix="/api", tags=["Audit"])


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
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
"""
Skill-0 Governance Dashboard API

FastAPI application providing REST APIs for the governance dashboard.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import stats, skills, reviews, scans, audit

app = FastAPI(
    title="Skill-0 Governance Dashboard API",
    description="REST API for the Skill-0 governance dashboard providing security scanning, equivalence testing, and approval workflow management.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stats.router, prefix="/api", tags=["Stats"])
app.include_router(skills.router, prefix="/api", tags=["Skills"])
app.include_router(reviews.router, prefix="/api", tags=["Reviews"])
app.include_router(scans.router, prefix="/api", tags=["Scans"])
app.include_router(audit.router, prefix="/api", tags=["Audit"])


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
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
