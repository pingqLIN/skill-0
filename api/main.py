"""
Skill-0 REST API
FastAPI integration with vector search and analysis features
"""

from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, TYPE_CHECKING, Literal
from dataclasses import asdict
import atexit
import hashlib
import os
import logging
import sqlite3
import hmac
from pathlib import Path
import time
import uuid
import ipaddress
from contextvars import ContextVar
from contextlib import contextmanager
from urllib.parse import urlparse

import structlog
from asset_registry.search import BoundedSearchExecutor, SearchOverloadedError
from api.logging_config import setup_logging
from api.routers.runs_v4 import (
    RUNTIME_BINDING_KEY_ENV,
    RUNTIME_DECISION_ACTORS_ENV,
    RUNTIME_HITL_TTL_SECONDS_ENV,
    RUNTIME_JOURNAL_MODE_ENV,
    router as runs_v4_router,
    runtime_binding_key_configuration_issue,
    runtime_hitl_ttl_configuration_issue,
    runtime_journal_mode_configuration_issue,
    get_asset_repository,
    reload_asset_repository,
)
from asset_registry.repositories import (
    AssetIdentityAmbiguousError,
    AssetNotFoundError,
    AssetRepository,
    StaleSourceSnapshotError,
)

# 初始化結構化日誌
_log_format = os.getenv("SKILL0_LOG_FORMAT", "json").lower()
setup_logging(
    log_level=os.getenv("SKILL0_LOG_LEVEL", "INFO"),
    json_format=(_log_format == "json"),
)
logger = structlog.get_logger(__name__)


def generate_request_id() -> str:
    """Generate a short unique request ID."""
    return uuid.uuid4().hex[:8]


request_id_var: ContextVar[str] = ContextVar('request_id', default='')

# Ensure vector_db module can be found
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

if TYPE_CHECKING:
    from vector_db import SemanticSearch

# Configuration
DB_PATH = os.getenv('SKILL0_DB_PATH', 'skills.db')
PARSED_DIR = os.getenv('SKILL0_PARSED_DIR', 'parsed')
SKILL0_ENV = os.getenv('SKILL0_ENV', 'development').lower()
DEFAULT_JWT_SECRET_KEY = 'dev-secret-change-in-production'
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CORS_ORIGINS',
        'http://localhost:5173,http://localhost:3000',
    ).split(',')
    if origin.strip()
]
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', DEFAULT_JWT_SECRET_KEY)
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_EXPIRE_MINUTES = int(os.getenv('JWT_EXPIRE_MINUTES', '30'))
API_RATE_LIMIT = os.getenv('API_RATE_LIMIT', '100/minute')
AUTH_RATE_LIMIT = os.getenv('AUTH_RATE_LIMIT', '10/minute')
API_USERNAME_ENV = "API_USERNAME"
API_PASSWORD_ENV = "API_PASSWORD"
API_VERSION = "2.4.0"

# Startup timestamp (module import time)
_startup_time = time.time()


def is_production_env(env_value: str) -> bool:
    """Return True when environment value represents production."""
    return env_value.strip().lower() in {'production', 'prod'}


def _env_flag(name: str, default: bool) -> bool:
    """Parse a boolean environment flag."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def _is_local_origin(origin: str) -> bool:
    """Detect localhost/loopback or wildcard CORS entries."""
    if origin.strip() == '*':
        return True

    parsed = urlparse(origin)
    host = (parsed.hostname or '').lower()
    return host in {'localhost', '127.0.0.1', '::1'}


def find_production_security_issues(
    env_value: str,
    cors_origins: List[str],
    jwt_secret_key: str,
    default_jwt_secret_key: str,
    configured_username: Optional[str],
    configured_password: Optional[str],
    runtime_binding_key: Optional[str] = None,
    runtime_decision_actors: Optional[str] = None,
    runtime_hitl_ttl_seconds: Optional[str] = None,
    runtime_journal_mode: Optional[str] = None,
    validate_runtime: bool = False,
) -> List[str]:
    """Enumerate production security misconfigurations."""
    if not is_production_env(env_value):
        return []

    issues: List[str] = []

    if jwt_secret_key == default_jwt_secret_key:
        issues.append('JWT_SECRET_KEY must not use the development default in production')

    insecure_origins = [origin for origin in cors_origins if _is_local_origin(origin)]
    if insecure_origins:
        issues.append(
            f'CORS_ORIGINS must not include localhost/wildcard in production: {", ".join(insecure_origins)}'
        )

    if not configured_username or not configured_password:
        issues.append(
            'API_USERNAME and API_PASSWORD must both be configured in production'
        )

    if validate_runtime:
        runtime_issue = runtime_binding_key_configuration_issue(
            runtime_binding_key,
            jwt_secret_key=jwt_secret_key,
        )
        if runtime_issue is not None:
            issues.append(runtime_issue)
        decision_actors = {
            actor.strip()
            for actor in (runtime_decision_actors or '').split(',')
            if actor.strip()
        }
        if not decision_actors or any(
            actor.lower().startswith(("change_me", "change-me"))
            for actor in decision_actors
        ):
            issues.append(
                'SKILL0_RUNTIME_DECISION_ACTORS must name explicit approver subjects'
            )
        ttl_issue = runtime_hitl_ttl_configuration_issue(runtime_hitl_ttl_seconds)
        if ttl_issue is not None:
            issues.append(ttl_issue)
        journal_issue = runtime_journal_mode_configuration_issue(
            runtime_journal_mode,
            require_wal=True,
        )
        if journal_issue is not None:
            issues.append(journal_issue)

    return issues


def enforce_production_security_configuration() -> None:
    """Fail fast when production security settings are unsafe."""
    issues = find_production_security_issues(
        env_value=SKILL0_ENV,
        cors_origins=CORS_ORIGINS,
        jwt_secret_key=JWT_SECRET_KEY,
        default_jwt_secret_key=DEFAULT_JWT_SECRET_KEY,
        configured_username=os.getenv(API_USERNAME_ENV),
        configured_password=os.getenv(API_PASSWORD_ENV),
        runtime_binding_key=os.getenv(RUNTIME_BINDING_KEY_ENV),
        runtime_decision_actors=os.getenv(RUNTIME_DECISION_ACTORS_ENV),
        runtime_hitl_ttl_seconds=os.getenv(RUNTIME_HITL_TTL_SECONDS_ENV),
        runtime_journal_mode=os.getenv(RUNTIME_JOURNAL_MODE_ENV),
        validate_runtime=True,
    )
    if issues:
        raise RuntimeError(
            'Invalid production security configuration: ' + '; '.join(issues)
        )


enforce_production_security_configuration()
ENABLE_DOCS = _env_flag(
    'SKILL0_ENABLE_DOCS',
    default=not is_production_env(SKILL0_ENV),
)

# FastAPI application
app = FastAPI(
    title="Skill-0 API",
    description="Claude Skills & MCP Tools Semantic Search API",
    version=API_VERSION,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

# CORS — controlled by CORS_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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
SEARCH_FAILURES = Counter(
    "skill0_search_failures_total",
    "Total search backend failures",
    ["endpoint", "reason"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Add request ID, structured logging, and metrics to every request"""
    rid = generate_request_id()
    request_id_var.set(rid)
    structlog.contextvars.bind_contextvars(request_id=rid)
    start = time.time()
    method = request.method
    path = request.url.path

    logger.info("request_started", method=method, path=path)

    # Apply baseline API rate limit to non-health/docs endpoints.
    if not _is_rate_limit_exempt_path(path):
        try:
            await check_rate_limit(request)
        except HTTPException as exc:
            duration = time.time() - start
            response = JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
            response.headers["X-Request-ID"] = rid
            REQUEST_COUNT.labels(method=method, endpoint=path, status=exc.status_code).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)
            logger.warning(
                "request_rate_limited",
                method=method,
                path=path,
                status=exc.status_code,
                duration_ms=round(duration * 1000, 2),
            )
            return response

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
    structlog.contextvars.unbind_contextvars("request_id")
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

RATE_LIMIT_EXEMPT_PATHS = {
    '/',
    '/health',
    '/api/health/detail',
    '/metrics',
    '/docs',
    '/redoc',
    '/openapi.json',
}


def _is_rate_limit_exempt_path(path: str) -> bool:
    """Paths exempt from API baseline rate limiting."""
    if path in RATE_LIMIT_EXEMPT_PATHS:
        return True
    return path.startswith('/docs/') or path.startswith('/redoc/')


def _parse_rate_limit(limit_str: str) -> tuple:
    """Parse rate limit string like '100/minute' -> (100, 60)"""
    parts = limit_str.split('/')
    if not parts or not parts[0].isdigit():
        raise ValueError(f"Invalid rate limit format: {limit_str}")
    count = int(parts[0])
    period_map = {'second': 1, 'minute': 60, 'hour': 3600}
    if len(parts) == 1:
        period = 60
    else:
        if parts[1] not in period_map:
            raise ValueError(f"Invalid rate limit window: {limit_str}")
        period = period_map[parts[1]]
    return count, period


def _parse_proxy_ip(value: Optional[str]) -> Optional[str]:
    """Return a normalized IP string when the candidate is valid."""
    if not value:
        return None

    candidate = value.strip()
    if not candidate:
        return None

    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _trusted_proxy_networks() -> list[ipaddress._BaseNetwork]:
    """Parse trusted proxy CIDRs from environment, skipping invalid entries."""
    cidr_text = os.getenv("SKILL0_TRUSTED_PROXY_CIDRS", "")
    networks: list[ipaddress._BaseNetwork] = []
    for raw_cidr in cidr_text.split(","):
        cidr = raw_cidr.strip()
        if not cidr:
            continue
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            logger.warning("invalid_trusted_proxy_cidr", cidr=cidr)
    return networks


def _proxy_headers_trusted(peer_host: Optional[str]) -> bool:
    """Return True only when proxy-header trust is enabled and the socket peer is trusted."""
    if not _env_flag("SKILL0_TRUST_PROXY_HEADERS", default=False):
        return False

    peer_ip = _parse_proxy_ip(peer_host)
    if peer_ip is None:
        return False

    peer_address = ipaddress.ip_address(peer_ip)
    return any(peer_address in network for network in _trusted_proxy_networks())


def _extract_client_ip(request: Request) -> str:
    """Extract the effective client IP, honoring trusted proxy headers when enabled."""
    peer_host = request.client.host if request.client else "unknown"
    if not _proxy_headers_trusted(peer_host):
        return peer_host

    forwarded_candidates = [
        ("CF-Connecting-IP", request.headers.get("CF-Connecting-IP")),
        (
            "X-Forwarded-For",
            next(
                (
                    part.strip()
                    for part in request.headers.get("X-Forwarded-For", "").split(",")
                    if part.strip()
                ),
                None,
            ),
        ),
        ("X-Real-IP", request.headers.get("X-Real-IP")),
    ]

    for header_name, raw_value in forwarded_candidates:
        if not raw_value:
            continue
        parsed_ip = _parse_proxy_ip(raw_value)
        if parsed_ip:
            return parsed_ip
        logger.warning(
            "invalid_forwarded_ip_header",
            header=header_name,
            value=raw_value,
            peer_host=peer_host,
        )

    return peer_host


def _search_service_unavailable(endpoint: str, exc: Exception) -> HTTPException:
    """Return a structured 503 without leaking backend/runtime details."""
    request_id = request_id_var.get() or generate_request_id()
    SEARCH_FAILURES.labels(endpoint=endpoint, reason="backend_unavailable").inc()
    logger.exception(
        "search_backend_unavailable",
        endpoint=endpoint,
        request_id=request_id,
        error_type=type(exc).__name__,
        error=str(exc),
    )
    return HTTPException(
        status_code=503,
        detail={
            "code": "SEARCH_BACKEND_UNAVAILABLE",
            "message": "Search service is temporarily unavailable.",
            "request_id": request_id,
        },
    )


async def check_rate_limit(request: Request):
    """Rate limit dependency for baseline API traffic."""
    await _enforce_rate_limit(request=request, limit_str=API_RATE_LIMIT, scope='api')


async def check_auth_rate_limit(request: Request):
    """Stricter rate limit dependency for auth token endpoint."""
    await _enforce_rate_limit(request=request, limit_str=AUTH_RATE_LIMIT, scope='auth')


async def _enforce_rate_limit(request: Request, limit_str: str, scope: str):
    """Shared rate-limit implementation with scope separation."""
    client_ip = _extract_client_ip(request)
    try:
        max_requests, period = _parse_rate_limit(limit_str)
    except ValueError as exc:
        logger.error(
            "invalid_rate_limit_configuration",
            scope=scope,
            limit=limit_str,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail="Rate limit misconfiguration")
    now = time.time()
    bucket_key = f"{scope}:{client_ip}"

    async with _rate_lock:
        # Purge expired entries
        _rate_limit_store[bucket_key] = [
            t for t in _rate_limit_store[bucket_key] if now - t < period
        ]
        if len(_rate_limit_store[bucket_key]) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({scope}). Max {max_requests} requests per {period}s.",
            )
        _rate_limit_store[bucket_key].append(now)


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


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Dependency that requires valid JWT for protected endpoints"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    principal = decode_access_token(credentials.credentials)
    request.state.auth_user = principal
    return principal


def validate_login_credentials(username: str, password: str) -> bool:
    """Validate API login credentials from environment configuration."""
    configured_username = os.getenv(API_USERNAME_ENV)
    configured_password = os.getenv(API_PASSWORD_ENV)

    if not configured_username or not configured_password:
        logger.error(
            "auth_configuration_missing",
            username_env=API_USERNAME_ENV,
            password_env=API_PASSWORD_ENV,
            username_configured=bool(configured_username),
            password_configured=bool(configured_password),
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication is not configured. "
                "Set API_USERNAME and API_PASSWORD environment variables."
            ),
        )

    username_matches = _constant_time_text_equal(username, configured_username)
    password_matches = _constant_time_text_equal(password, configured_password)
    return username_matches and password_matches


def _constant_time_text_equal(value: str, expected: str) -> bool:
    """Compare arbitrary text through fixed-length digests."""
    value_digest = hashlib.sha256(value.encode("utf-8")).digest()
    expected_digest = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(value_digest, expected_digest)

# Global search engine (lazy initialization)
search_engine: Optional["SemanticSearch"] = None
search_executor = BoundedSearchExecutor(max_workers=2, queue_capacity=4)
atexit.register(search_executor.shutdown)


def _load_semantic_search_class():
    """Lazy-load SemanticSearch to avoid heavy ML imports at API startup."""
    from vector_db import SemanticSearch

    return SemanticSearch


def get_search_engine() -> "SemanticSearch":
    """Get or initialize search engine"""
    global search_engine
    if search_engine is None:
        SemanticSearch = _load_semantic_search_class()
        search_engine = SemanticSearch(db_path=DB_PATH, initialize_schema=False)
    return search_engine


def _get_db_skill_count(db_path: str) -> int:
    """Read total skill rows directly from SQLite without initializing the embedder."""
    resolved = Path(db_path).resolve()
    with sqlite3.connect(f"file:{resolved.as_posix()}?mode=ro", uri=True) as conn:
        row = conn.execute('SELECT COUNT(*) FROM skills').fetchone()
    return int(row[0] if row else 0)


@contextmanager
def _search_unit_of_work():
    engine = get_search_engine()
    if getattr(type(engine), "open_unit_of_work", None) is None:
        yield engine
        return
    with engine.open_unit_of_work() as operation_engine:
        yield operation_engine


def _search_sync(query: str, limit: int):
    with _search_unit_of_work() as engine:
        return engine.search(query, limit=limit)


def _similar_sync(skill_name: str, limit: int):
    with _search_unit_of_work() as engine:
        return engine.find_similar(skill_name, limit=limit)


def _cluster_sync(n_clusters: int):
    with _search_unit_of_work() as engine:
        return engine.cluster_skills(n_clusters=n_clusters)


def _stats_sync():
    with _search_unit_of_work() as engine:
        return engine.get_statistics()


def _list_skills_sync():
    with _search_unit_of_work() as engine:
        return engine.store.get_all_skills()


def _skill_by_id_sync(skill_id: int, include_json: bool):
    with _search_unit_of_work() as engine:
        return engine.store.get_skill_by_id(skill_id, include_json=include_json)


def _index_sync(parsed_dir: str) -> int:
    with _search_unit_of_work() as engine:
        if engine.store.has_asset_index_state():
            return engine.index_assets(parsed_dir, show_progress=False).changed
        return engine.index_skills(parsed_dir, show_progress=False)


def _asset_search_sync(query: str, asset_types: tuple[str, ...], limit: int):
    with _search_unit_of_work() as engine:
        return engine.search_assets(query, asset_types=asset_types, limit=limit)


def _search_overloaded(exc: SearchOverloadedError) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={"code": exc.code, "message": "Search capacity is exhausted"},
        headers={"Retry-After": "1"},
    )


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


class AssetSummary(BaseModel):
    asset_id: str
    asset_type: Literal["skill"]
    name: str
    summary: str
    revision_count: int
    ambiguous: bool


class AssetRevisionResponse(BaseModel):
    asset_id: str
    revision_id: str
    asset_type: Literal["skill"]
    content_hash: str
    source_digest: str
    source_path: str
    payload: dict[str, Any] | None = None


class AssetSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    asset_types: list[Literal["skill"]] = Field(default_factory=lambda: ["skill"])
    limit: int = Field(default=5, ge=1, le=50)


class AssetReloadResponse(BaseModel):
    snapshot_id: str
    revision_count: int
    ambiguous_asset_ids: list[str]
    ambiguous_legacy_aliases: list[str]


def _revision_response(revision, *, include_payload: bool) -> AssetRevisionResponse:
    return AssetRevisionResponse(
        asset_id=revision.asset_id,
        revision_id=revision.revision_id,
        asset_type="skill",
        content_hash=revision.content_hash,
        source_digest=revision.source_digest,
        source_path=revision.source_path.as_posix(),
        payload=revision.payload if include_payload else None,
    )


def _raise_asset_repository_error(exc: Exception) -> None:
    if isinstance(exc, AssetNotFoundError):
        raise HTTPException(status_code=404, detail="Asset not found") from exc
    if isinstance(exc, StaleSourceSnapshotError):
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": "Asset source snapshot changed"},
        ) from exc
    if isinstance(exc, AssetIdentityAmbiguousError):
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": "Asset identity is ambiguous"},
        ) from exc
    raise exc


@app.get("/api/assets", response_model=list[AssetSummary], tags=["Assets"])
async def list_assets(
    repository: AssetRepository = Depends(get_asset_repository),
):
    try:
        revisions = await search_executor.run(repository.list_revisions)
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    except Exception as exc:
        _raise_asset_repository_error(exc)
    grouped: dict[str, list] = {}
    for revision in revisions:
        grouped.setdefault(revision.asset_id, []).append(revision)
    return [
        AssetSummary(
            asset_id=asset_id,
            asset_type="skill",
            name=str(items[0].payload.get("meta", {}).get("name") or asset_id),
            summary=str(items[0].payload.get("meta", {}).get("description") or ""),
            revision_count=len(items),
            ambiguous=len(items) > 1,
        )
        for asset_id, items in sorted(grouped.items())
    ]


@app.get(
    "/api/assets/{asset_id}/revisions",
    response_model=list[AssetRevisionResponse],
    tags=["Assets"],
)
async def list_asset_revisions(
    asset_id: str,
    repository: AssetRepository = Depends(get_asset_repository),
):
    try:
        revisions = await search_executor.run(
            repository.list_asset_revisions, asset_id
        )
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    except Exception as exc:
        _raise_asset_repository_error(exc)
    return [_revision_response(item, include_payload=False) for item in revisions]


@app.get(
    "/api/assets/{asset_id}",
    response_model=AssetRevisionResponse,
    tags=["Assets"],
)
async def get_asset(
    asset_id: str,
    include_payload: bool = Query(False),
    repository: AssetRepository = Depends(get_asset_repository),
):
    try:
        revision = await search_executor.run(repository.get_revision, asset_id)
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    except Exception as exc:
        _raise_asset_repository_error(exc)
    return _revision_response(revision, include_payload=include_payload)


@app.post("/api/assets/search", tags=["Assets"])
async def search_assets(request: AssetSearchRequest):
    try:
        results = await search_executor.run(
            _asset_search_sync,
            request.query,
            tuple(request.asset_types),
            request.limit,
        )
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    except Exception as exc:
        raise _search_service_unavailable("/api/assets/search", exc) from exc
    return {
        "query": request.query,
        "results": [asdict(item) for item in results],
        "count": len(results),
    }


@app.post(
    "/api/assets/reload",
    response_model=AssetReloadResponse,
    tags=["Assets"],
)
async def reload_assets(_user: dict = Depends(require_auth)):
    """Validate and atomically swap the configured Runtime Asset snapshot."""

    try:
        repository = await search_executor.run(reload_asset_repository)
        revisions = repository.list_revisions()
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    except Exception as exc:
        _raise_asset_repository_error(exc)
    return AssetReloadResponse(
        snapshot_id=repository.snapshot_id,
        revision_count=len(revisions),
        ambiguous_asset_ids=list(repository.ambiguous_asset_ids),
        ambiguous_legacy_aliases=list(repository.ambiguous_legacy_aliases),
    )


# ==================== Endpoints ====================

@app.get("/", tags=["Root"])
async def root():
    """API root path"""
    return {
        "name": "Skill-0 API",
        "version": API_VERSION,
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
    """Cheap liveness/readiness check that does not require loading the embedding model."""
    try:
        total_skills = _get_db_skill_count(DB_PATH)
        return {
            "status": "healthy",
            "db_path": DB_PATH,
            "total_skills": total_skills,
        }
    except Exception as exc:
        logger.exception(
            "health_check_failed",
            db_path=DB_PATH,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        raise HTTPException(status_code=503, detail="Service unavailable") from exc


class HealthDetailResponse(BaseModel):
    """Detailed health check response"""
    status: str = Field(..., description="Overall health status: healthy or degraded")
    db_path: str
    db_exists: bool
    db_size_bytes: int
    total_skills: int
    embedding_model: str
    uptime_seconds: float
    version: str = Field(API_VERSION, description="API version")


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

    total_skills = 0
    embedding_model = "all-MiniLM-L6-v2"
    status = "healthy"

    if db_exists:
        try:
            total_skills = _get_db_skill_count(db_path)
        except Exception:
            status = "degraded"
            total_skills = 0
    else:
        status = "degraded"

    # If the search engine is already warm, surface its configured model name
    # without forcing a model initialization from the health endpoint.
    if search_engine is not None:
        try:
            stats = search_engine.get_statistics()
            if isinstance(stats, dict):
                embedding_model = stats.get('model_name', embedding_model) or embedding_model
        except Exception:
            status = "degraded"

    return HealthDetailResponse(
        status=status,
        db_path=db_path,
        db_exists=db_exists,
        db_size_bytes=db_size_bytes,
        total_skills=total_skills,
        embedding_model=embedding_model,
        uptime_seconds=uptime_seconds,
        version=API_VERSION,
    )


@app.post("/api/search", response_model=SearchResponse, tags=["Search"])
async def search_skills(request: SearchRequest):
    """
    Semantic search for Skills
    
    Use natural language query to find relevant skills.
    """
    start = time.time()
    
    try:
        results = await search_executor.run(_search_sync, request.query, request.limit)
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    except Exception as exc:
        raise _search_service_unavailable("/api/search", exc) from exc
    
    elapsed = (time.time() - start) * 1000
    
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
    
    try:
        results = await search_executor.run(_search_sync, q, limit)
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    except Exception as exc:
        raise _search_service_unavailable("/api/search", exc) from exc
    
    elapsed = (time.time() - start) * 1000
    
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
    
    try:
        results = await search_executor.run(
            _similar_sync, request.skill_name, request.limit
        )
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    except Exception as exc:
        raise _search_service_unavailable("/api/similar", exc) from exc
    
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
    
    try:
        results = await search_executor.run(_similar_sync, skill_name, limit)
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    except Exception as exc:
        raise _search_service_unavailable("/api/similar", exc) from exc
    
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
    try:
        clusters = await search_executor.run(_cluster_sync, n)
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    except Exception as exc:
        raise _search_service_unavailable("/api/cluster", exc) from exc
    
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
    try:
        stats = await search_executor.run(_stats_sync)
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    
    return StatsResponse(**stats)


@app.get("/api/skills", tags=["Info"])
async def list_all_skills(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """List all Skills (paginated)"""
    try:
        all_skills = await search_executor.run(_list_skills_sync)
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    
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
    try:
        skill = await search_executor.run(_skill_by_id_sync, skill_id, include_json)
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    
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
    
    try:
        count = await search_executor.run(_index_sync, request.parsed_dir)
    except SearchOverloadedError as exc:
        raise _search_overloaded(exc) from exc
    
    elapsed = time.time() - start
    
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
async def login(
    request: TokenRequest,
    _auth_rate_limit: None = Depends(check_auth_rate_limit),
):
    """
    Get access token

    Validates credentials against environment variables:
    API_USERNAME and API_PASSWORD.
    """
    if not validate_login_credentials(request.username, request.password):
        logger.warning("login_failed", username=request.username)
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

# ==================== Runtime Governance v4 Endpoints ====================

app.include_router(runs_v4_router, dependencies=[Depends(require_auth)])



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
║              Skill-0 API Server v{API_VERSION:<24}║
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
