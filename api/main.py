"""
Skill-0 REST API
FastAPI integration with vector search and analysis features
"""

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
from pathlib import Path
import time

from api.logging_config import configure_logging, get_logger, generate_request_id, request_id_var

# Initialize structured logging
configure_logging()
logger = get_logger(__name__)

# Ensure vector_db module can be found
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from vector_db import SemanticSearch

# Configuration
DB_PATH = os.getenv('SKILL0_DB_PATH', 'skills.db')
PARSED_DIR = os.getenv('SKILL0_PARSED_DIR', 'parsed')
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:3000').split(',')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-change-in-production')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXPIRE_MINUTES = int(os.getenv('JWT_EXPIRE_MINUTES', '30'))
API_RATE_LIMIT = os.getenv('API_RATE_LIMIT', '100/minute')

# Startup timestamp (module import time)
_startup_time = time.time()

# FastAPI application
app = FastAPI(
    title="Skill-0 API",
    description="Claude Skills & MCP Tools Semantic Search API",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — controlled by CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Prometheus Metrics ====================

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUEST_COUNT = Counter(
    "skill0_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "skill0_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)
SEARCH_LATENCY = Histogram(
    "skill0_search_duration_seconds",
    "Search operation latency in seconds",
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Add request ID, structured logging, and metrics to every request"""
    rid = generate_request_id()
    request_id_var.set(rid)
    start = time.time()
    method = request.method
    path = request.url.path

    logger.info("request_started", method=method, path=path)

    response = await call_next(request)

    duration = time.time() - start
    status = response.status_code
    response.headers["X-Request-ID"] = rid

    REQUEST_COUNT.labels(method=method, endpoint=path, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

    logger.info(
        "request_completed",
        method=method,
        path=path,
        status=status,
        duration_ms=round(duration * 1000, 2),
    )
    return response


@app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ==================== Rate Limiting ====================

from collections import defaultdict
import asyncio

_rate_limit_store: Dict[str, list] = defaultdict(list)
_rate_lock = asyncio.Lock()


def _parse_rate_limit(limit_str: str) -> tuple:
    """Parse rate limit string like '100/minute' -> (100, 60)"""
    parts = limit_str.split('/')
    count = int(parts[0])
    period_map = {'second': 1, 'minute': 60, 'hour': 3600}
    period = period_map.get(parts[1], 60) if len(parts) > 1 else 60
    return count, period


async def check_rate_limit(request: Request):
    """Rate limiting dependency for protected endpoints"""
    client_ip = request.client.host if request.client else "unknown"
    max_requests, period = _parse_rate_limit(API_RATE_LIMIT)
    now = time.time()

    async with _rate_lock:
        # Purge expired entries
        _rate_limit_store[client_ip] = [
            t for t in _rate_limit_store[client_ip] if now - t < period
        ]
        if len(_rate_limit_store[client_ip]) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {period}s.",
            )
        _rate_limit_store[client_ip].append(now)


# ==================== JWT Authentication ====================

import jwt
from datetime import datetime, timedelta, timezone

security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency that requires valid JWT for protected endpoints"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return decode_access_token(credentials.credentials)

# Global search engine (lazy initialization)
search_engine: Optional[SemanticSearch] = None


def get_search_engine() -> SemanticSearch:
    """Get or initialize search engine"""
    global search_engine
    if search_engine is None:
        search_engine = SemanticSearch(db_path=DB_PATH)
    return search_engine


# ==================== Models ====================

class SkillResult(BaseModel):
    """Skill search result"""
    id: int
    name: str
    filename: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    action_count: int = 0
    rule_count: int = 0
    directive_count: int = 0
    created_at: Optional[str] = None
    similarity: Optional[float] = None
    distance: Optional[float] = None


class SearchRequest(BaseModel):
    """Search request"""
    query: str = Field(..., description="Search query", min_length=1)
    limit: int = Field(5, description="Number of results", ge=1, le=50)


class SearchResponse(BaseModel):
    """Search response"""
    query: str
    results: List[SkillResult]
    count: int
    latency_ms: float


class SimilarRequest(BaseModel):
    """Similar search request"""
    skill_name: str = Field(..., description="Skill name")
    limit: int = Field(5, description="Number of results", ge=1, le=50)


class ClusterResponse(BaseModel):
    """Cluster response"""
    clusters: Dict[int, List[SkillResult]]
    total_skills: int
    n_clusters: int


class StatsResponse(BaseModel):
    """Statistics response"""
    total_skills: int
    total_actions: int
    total_rules: int
    total_directives: int
    embedding_dimension: int
    model_name: str
    categories: Dict[str, int]


class IndexRequest(BaseModel):
    """Index request"""
    parsed_dir: str = Field(PARSED_DIR, description="Parsed directory path")


class IndexResponse(BaseModel):
    """Index response"""
    indexed_count: int
    elapsed_seconds: float
    message: str


# ==================== Endpoints ====================

@app.get("/", tags=["Root"])
async def root():
    """API root path"""
    return {
        "name": "Skill-0 API",
        "version": "2.1.0",
        "description": "Claude Skills & MCP Tools Semantic Search API",
        "endpoints": {
            "search": "/api/search",
            "similar": "/api/similar",
            "cluster": "/api/cluster",
            "stats": "/api/stats",
            "skills": "/api/skills",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check"""
    try:
        engine = get_search_engine()
        stats = engine.get_statistics()
        return {
            "status": "healthy",
            "db_path": DB_PATH,
            "total_skills": stats['total_skills']
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")


class HealthDetailResponse(BaseModel):
    """Detailed health check response"""
    status: str = Field(..., description="Overall health status: healthy or degraded")
    db_path: str
    db_exists: bool
    db_size_bytes: int
    total_skills: int
    embedding_model: str
    uptime_seconds: float
    version: str = Field("2.1.0", description="API version")


@app.get("/api/health/detail", response_model=HealthDetailResponse, tags=["Health"])
async def health_detail():
    """Detailed health check including DB and runtime metrics"""
    # Basic, best-effort values
    db_path = DB_PATH
    db_exists = Path(db_path).exists()
    try:
        db_size_bytes = Path(db_path).stat().st_size if db_exists else 0
    except Exception:
        db_size_bytes = 0

    # Uptime since startup
    uptime_seconds = max(0.0, time.time() - _startup_time)

    # Defaults (in case engine fails)
    total_skills = 0
    embedding_model = "unknown"
    status = "healthy"
    try:
        engine = get_search_engine()
        stats = engine.get_statistics()
        if isinstance(stats, dict):
            total_skills = int(stats.get('total_skills', 0))
            embedding_model = stats.get('model_name', 'unknown') or 'unknown'
        else:
            total_skills = 0
            embedding_model = 'unknown'
    except Exception:
        # Degraded state if the engine cannot be queried
        status = "degraded"
        total_skills = 0
        embedding_model = "unknown"

    return HealthDetailResponse(
        status=status,
        db_path=db_path,
        db_exists=db_exists,
        db_size_bytes=db_size_bytes,
        total_skills=total_skills,
        embedding_model=embedding_model,
        uptime_seconds=uptime_seconds,
        version="2.1.0",
    )


@app.post("/api/search", response_model=SearchResponse, tags=["Search"])
async def search_skills(request: SearchRequest):
    """
    Semantic search for Skills
    
    Use natural language query to find relevant skills.
    """
    start = time.time()
    
    engine = get_search_engine()
    results = engine.search(request.query, limit=request.limit)
    
    elapsed = (time.time() - start) * 1000
    SEARCH_LATENCY.observe(elapsed / 1000)

    logger.info("search_completed", query=request.query, results=len(results), latency_ms=round(elapsed, 2))
    
    return SearchResponse(
        query=request.query,
        results=[SkillResult(**r) for r in results],
        count=len(results),
        latency_ms=round(elapsed, 2)
    )


@app.get("/api/search", response_model=SearchResponse, tags=["Search"])
async def search_skills_get(
    q: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(5, description="Number of results", ge=1, le=50)
):
    """
    Semantic search for Skills (GET)
    
    Use natural language query to find relevant skills.
    """
    start = time.time()
    
    engine = get_search_engine()
    results = engine.search(q, limit=limit)
    
    elapsed = (time.time() - start) * 1000
    SEARCH_LATENCY.observe(elapsed / 1000)

    logger.info("search_completed", query=q, results=len(results), latency_ms=round(elapsed, 2))
    
    return SearchResponse(
        query=q,
        results=[SkillResult(**r) for r in results],
        count=len(results),
        latency_ms=round(elapsed, 2)
    )


@app.post("/api/similar", response_model=SearchResponse, tags=["Search"])
async def find_similar_skills(request: SimilarRequest):
    """
    Find similar Skills
    
    Find other skills with similar functionality based on the specified skill name.
    """
    start = time.time()
    
    engine = get_search_engine()
    results = engine.find_similar(request.skill_name, limit=request.limit)
    
    if not results:
        raise HTTPException(status_code=404, detail=f"Skill '{request.skill_name}' not found")
    
    elapsed = (time.time() - start) * 1000
    
    return SearchResponse(
        query=f"similar to: {request.skill_name}",
        results=[SkillResult(**r) for r in results],
        count=len(results),
        latency_ms=round(elapsed, 2)
    )


@app.get("/api/similar/{skill_name}", response_model=SearchResponse, tags=["Search"])
async def find_similar_skills_get(
    skill_name: str,
    limit: int = Query(5, description="Number of results", ge=1, le=50)
):
    """
    Find similar Skills (GET)
    """
    start = time.time()
    
    engine = get_search_engine()
    results = engine.find_similar(skill_name, limit=limit)
    
    if not results:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    
    elapsed = (time.time() - start) * 1000
    
    return SearchResponse(
        query=f"similar to: {skill_name}",
        results=[SkillResult(**r) for r in results],
        count=len(results),
        latency_ms=round(elapsed, 2)
    )


@app.get("/api/cluster", response_model=ClusterResponse, tags=["Analysis"])
async def cluster_skills(
    n: int = Query(5, description="Number of clusters", ge=2, le=20)
):
    """
    Skills cluster analysis
    
    Automatically group all skills using K-Means clustering.
    """
    engine = get_search_engine()
    clusters = engine.cluster_skills(n_clusters=n)
    
    # Convert format
    formatted_clusters = {}
    total = 0
    for cluster_id, skills in clusters.items():
        formatted_clusters[cluster_id] = [SkillResult(**s) for s in skills]
        total += len(skills)
    
    return ClusterResponse(
        clusters=formatted_clusters,
        total_skills=total,
        n_clusters=len(clusters)
    )


@app.get("/api/stats", response_model=StatsResponse, tags=["Info"])
async def get_statistics():
    """Get database statistics"""
    engine = get_search_engine()
    stats = engine.get_statistics()
    
    return StatsResponse(**stats)


@app.get("/api/skills", tags=["Info"])
async def list_all_skills(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """List all Skills (paginated)"""
    engine = get_search_engine()
    all_skills = engine.store.get_all_skills()
    
    # Pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated = all_skills[start:end]
    
    return {
        "skills": [SkillResult(**s) for s in paginated],
        "total": len(all_skills),
        "page": page,
        "per_page": per_page,
        "total_pages": (len(all_skills) + per_page - 1) // per_page
    }


@app.get("/api/skills/{skill_id}", tags=["Info"])
async def get_skill_by_id(
    skill_id: int,
    include_json: bool = Query(False, description="Include original JSON")
):
    """Get Skill details by ID"""
    engine = get_search_engine()
    skill = engine.store.get_skill_by_id(skill_id, include_json=include_json)
    
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill with ID {skill_id} not found")
    
    return skill


@app.post("/api/index", response_model=IndexResponse, tags=["Admin"])
async def index_skills(request: IndexRequest, _user: dict = Depends(require_auth)):
    """
    Re-index Skills (requires authentication)
    
    Rebuild vector index from parsed directory.
    """
    start = time.time()
    
    engine = get_search_engine()
    
    engine.store.clear()
    count = engine.index_skills(request.parsed_dir, show_progress=False)
    
    elapsed = time.time() - start
    logger.info("index_completed", count=count, elapsed_seconds=round(elapsed, 3))
    
    return IndexResponse(
        indexed_count=count,
        elapsed_seconds=round(elapsed, 3),
        message=f"Successfully indexed {count} skills"
    )


# ==================== Auth Endpoints ====================

class TokenRequest(BaseModel):
    """Token request"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@app.post("/api/auth/token", response_model=TokenResponse, tags=["Auth"])
async def login(request: TokenRequest):
    """
    Get access token

    In production, validate against a user store.
    Currently accepts any non-empty credentials for development.
    """
    # TODO: Replace with real user validation in production
    if not request.username or not request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": request.username})
    return TokenResponse(
        access_token=token,
        expires_in=JWT_EXPIRE_MINUTES * 60,
    )


@app.get("/api/auth/me", tags=["Auth"])
async def get_current_user(user: dict = Depends(require_auth)):
    """Get current authenticated user info"""
    return {"username": user.get("sub"), "exp": user.get("exp")}


# ==================== Startup ====================

def main():
    """Start API server"""
    import uvicorn
    
    # Ensure database exists
    if not Path(DB_PATH).exists():
        print(f"Database not found at {DB_PATH}, indexing skills...")
        engine = get_search_engine()
        engine.index_skills(PARSED_DIR, show_progress=True)
    
    print(f"""
╔════════════════════════════════════════════════════════════╗
║              Skill-0 API Server v2.1.0                     ║
╠════════════════════════════════════════════════════════════╣
║  API Docs:  http://127.0.0.1:8000/docs                     ║
║  ReDoc:     http://127.0.0.1:8000/redoc                    ║
║  Health:    http://127.0.0.1:8000/health                   ║
╚════════════════════════════════════════════════════════════╝
""")
    
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
