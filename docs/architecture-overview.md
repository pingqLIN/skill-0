# Architecture Overview

## System Diagram

```
                                  +-------------------+
                                  |   Web Frontend    |
                                  |  React + Vite     |
                                  |  Port 5173 (dev)  |
                                  |  Port 80 (prod)   |
                                  +--------+----------+
                                           |
                          +----------------+----------------+
                          |                                 |
                 +--------v----------+           +----------v--------+
                 |   Core API        |           |  Dashboard API    |
                 |   FastAPI         |           |  FastAPI          |
                 |   Port 8000       |           |  Port 8001        |
                 |                   |           |                   |
                 |  Semantic Search  |           |  Governance       |
                 |  JWT Auth         |           |  Skills CRUD      |
                 |  Rate Limiting    |           |  Reviews          |
                 |  Prometheus       |           |  Scans            |
                 +--------+----------+           |  Audit            |
                          |                      +----------+--------+
                          |                                 |
                 +--------v----------+           +----------v--------+
                 |   skills.db       |           |  governance.db    |
                 |   SQLite + vec    |           |  SQLite           |
                 |   Vector search   |           |  Workflow state   |
                 +-------------------+           +-------------------+
```

## Components

### Core API (port 8000)

The primary search and analysis API, implemented in `api/main.py`.

Responsibilities:
- Semantic search over indexed skills using vector embeddings
- Skill similarity and clustering analysis
- JWT-based authentication for write operations
- Rate limiting per client IP
- Prometheus metrics exposition

Middleware stack (applied in order):
1. CORS (origin whitelist from `CORS_ORIGINS`)
2. Request middleware (request ID, structured logging, Prometheus metrics)
3. Rate limiting (per-endpoint dependency injection)
4. JWT authentication (per-endpoint dependency injection)

Key endpoints:

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Basic health check |
| `/api/health/detail` | GET | No | Detailed health with DB metrics and uptime |
| `/api/search` | POST, GET | No | Semantic search |
| `/api/similar/{name}` | GET | No | Find similar skills |
| `/api/cluster` | GET | No | K-Means cluster analysis |
| `/api/stats` | GET | No | Database statistics |
| `/api/skills` | GET | No | Paginated skill listing |
| `/api/skills/{id}` | GET | No | Skill detail |
| `/api/index` | POST | JWT | Re-index skills |
| `/api/auth/token` | POST | No | Get JWT token |
| `/api/auth/me` | GET | JWT | Current user info |
| `/metrics` | GET | No | Prometheus metrics |

### Dashboard API (port 8001)

Governance workflow API, implemented in `skill-0-dashboard/apps/api/main.py`.

Responsibilities:
- Skill governance (approval/rejection workflows)
- Security scan management
- Audit trail logging
- Dashboard statistics

Router structure (all mounted at `/api` prefix):

| Router | Path | Description |
|--------|------|-------------|
| `stats` | `/api/stats` | Dashboard statistics |
| `skills` | `/api/skills` | Skill management |
| `reviews` | `/api/reviews` | Review workflows |
| `scans` | `/api/scans` | Security scans |
| `audit` | `/api/audit` | Audit log |

The Dashboard API is fully independent from the Core API. It has its own `requirements.txt`, logging configuration, and database.

### Web Frontend (port 5173 dev / port 80 prod)

React + TypeScript + Vite application in `skill-0-dashboard/apps/web/`.

Stack:
- React with TypeScript
- Vite build tool
- TailwindCSS for styling
- shadcn/ui component library
- `cn()` utility for class merging

In development, the Vite dev server proxies API calls. In production, nginx serves the built static files and proxies API requests to the backend services.

## Data Flow

### Skill Ingestion

```
Skill Markdown Files
        |
        v
tools/batch_parse.py  (uses advanced_skill_analyzer.py)
        |
        v
parsed/*.json  (32 structured skill JSONs, schema v2.1)
        |
        v
vector_db/search.py index  (SkillEmbedder + VectorStore)
        |
        v
skills.db  (SQLite + sqlite-vec virtual table)
```

### Search Query

```
User Query ("PDF processing")
        |
        v
POST /api/search  (FastAPI endpoint)
        |
        v
SemanticSearch.search()  (vector_db/search.py)
        |
        v
SkillEmbedder.embed()  (all-MiniLM-L6-v2, 384 dimensions)
        |
        v
VectorStore.search_similar()  (L2 distance via sqlite-vec)
        |
        v
Results ranked by similarity  (1/(1+distance))
```

## Database Schema

### skills.db

Contains two tables:

**`skills`** (metadata):

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `name` | TEXT | Skill name |
| `filename` | TEXT | Source JSON filename |
| `description` | TEXT | Skill description |
| `category` | TEXT | Skill category |
| `version` | TEXT | Schema version |
| `action_count` | INTEGER | Number of actions |
| `rule_count` | INTEGER | Number of rules |
| `directive_count` | INTEGER | Number of directives |
| `json_data` | TEXT | Full original JSON |
| `created_at` | TIMESTAMP | Index timestamp |

**`skill_vectors`** (sqlite-vec virtual table):

| Column | Type | Description |
|--------|------|-------------|
| `rowid` | INTEGER | Links to `skills.id` |
| `embedding` | FLOAT[384] | 384-dimensional vector |

### governance.db

Stores governance workflow state including skill records, review decisions, security scan results, and audit log entries. Located at `governance/db/governance.db`.

## Embedding Pipeline

| Property | Value |
|----------|-------|
| Model | `all-MiniLM-L6-v2` (sentence-transformers) |
| Dimensions | 384 |
| Distance metric | L2 (Euclidean) |
| Similarity conversion | `1 / (1 + distance)` |
| Device selection | `SKILL0_DEVICE` env: `auto` (CUDA if available, else CPU), `cpu`, `cuda` |
| Storage | `sqlite-vec` virtual table |
| Index time | ~0.88s for 32 skills |
| Search latency | ~75ms |

The embedder (`vector_db/embedder.py`) resolves the device at initialization via `_resolve_device()`:
1. If `SKILL0_DEVICE=cuda` and CUDA is available, use GPU
2. If `SKILL0_DEVICE=cpu`, force CPU
3. If `SKILL0_DEVICE=auto` (default), auto-detect CUDA availability with CPU fallback

## Security Architecture

### JWT Authentication

- Token-based auth using PyJWT with HS256 signing
- `POST /api/auth/token` issues tokens (currently accepts any non-empty credentials; implement real validation for production)
- Protected endpoints use `require_auth` dependency
- Tokens include `sub` (username) and `exp` (expiration) claims
- Configurable expiration via `JWT_EXPIRE_MINUTES`

### Rate Limiting

- In-memory async rate limiter keyed by client IP
- Configurable via `API_RATE_LIMIT` (e.g., `100/minute`, `1000/hour`)
- Returns HTTP 429 when exceeded
- Applied as a FastAPI dependency on endpoints

### CORS

- Origins controlled by `CORS_ORIGINS` environment variable
- Both APIs parse comma-separated origin list
- Default allows `localhost:5173` and `localhost:3000` for development
- Must be restricted to actual domains in production

## Directory Structure

```
skill-0/
├── api/                          # Core API
│   ├── main.py                   # FastAPI app (search, auth, metrics)
│   └── logging_config.py         # Structured logging configuration
├── vector_db/                    # Vector search engine
│   ├── search.py                 # SemanticSearch class + CLI
│   ├── vector_store.py           # VectorStore (SQLite + sqlite-vec)
│   └── embedder.py               # SkillEmbedder (sentence-transformers)
├── tools/                        # CLI utilities
│   ├── batch_parse.py            # Parse skills to JSON
│   ├── batch_security_scan.py    # Security scanner
│   ├── skill_governance.py       # Governance workflow CLI
│   ├── governance_db.py          # Governance database module
│   └── advanced_skill_analyzer.py # Skill analysis engine
├── parsed/                       # 32 parsed skill JSONs
├── schema/                       # JSON Schema v2.1
├── governance/                   # Governance data
│   └── db/governance.db          # Governance SQLite database
├── converted-skills/             # 171 imported skills (raw)
├── scripts/
│   ├── backup_db.sh              # Database backup script
│   └── helper.py                 # Validation/conversion utilities
├── tests/
│   ├── test_helper.py            # Unit tests (32 tests)
│   └── integration/              # Integration tests (63 tests)
├── skill-0-dashboard/            # Dashboard monorepo
│   └── apps/
│       ├── api/                  # Dashboard API (FastAPI, port 8001)
│       └── web/                  # Dashboard UI (React + Vite)
├── skills.db                     # Vector search database
├── docker-compose.yml            # Dev compose
├── docker-compose.prod.yml       # Prod overrides
├── Dockerfile.api                # Core API container
├── Dockerfile.dashboard          # Dashboard API container
├── Dockerfile.web                # Web frontend container
├── .env.example                  # Dev environment template
├── .env.production.example       # Prod environment template
└── .github/workflows/ci.yml     # CI pipeline
```
