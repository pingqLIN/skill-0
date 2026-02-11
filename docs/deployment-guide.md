# Deployment Guide

## Prerequisites

- Python 3.12+
- Node.js 20+ and npm
- Docker and Docker Compose (for containerized deployment)
- SQLite 3.35+ (for WAL mode and `.backup` command)

## Environment Configuration

Copy the appropriate example file and customize:

```bash
# Development
cp .env.example .env

# Production
cp .env.production.example .env
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SKILL0_DB_PATH` | `skills.db` | Path to the vector search SQLite database |
| `SKILL0_PARSED_DIR` | `parsed` | Directory containing parsed skill JSONs |
| `SKILL0_GOVERNANCE_DB_PATH` | `governance/db/governance.db` | Path to governance database |
| `SKILL0_TOOLS_PATH` | `tools` | Path to tools directory |
| `SKILL0_DEVICE` | `auto` | Embedding device: `auto`, `cpu`, or `cuda` |
| `SKILL0_LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `SKILL0_LOG_FORMAT` | `json` | Log format: `json` (production) or `console` (dev) |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed origins |
| `JWT_SECRET_KEY` | `dev-secret-change-in-production` | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRE_MINUTES` | `30` | Token expiration in minutes |
| `API_RATE_LIMIT` | `100/minute` | Rate limit format: `{count}/{period}` |

## Local Development Setup

### 1. Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Index Skills (first time)

```bash
python -m vector_db.search --db skills.db --parsed-dir parsed index
```

### 3. Start Core API (port 8000)

```bash
python -m api.main
```

Endpoints:
- API docs: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health: http://127.0.0.1:8000/health
- Metrics: http://127.0.0.1:8000/metrics

### 4. Start Dashboard API (port 8001)

```bash
cd skill-0-dashboard/apps/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Endpoints:
- API docs: http://localhost:8001/docs
- Health: http://localhost:8001/health

### 5. Start Web Frontend (port 5173)

```bash
cd skill-0-dashboard/apps/web
npm install
npm run dev
```

Dashboard: http://localhost:5173

## Docker Deployment

### Development

```bash
docker compose up --build
```

Services:
- Core API: http://localhost:8000
- Dashboard API: http://localhost:8001
- Web UI: http://localhost:3000

### Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Production overrides:
- Volume mounts removed (code baked into images)
- `restart: always` policy
- Resource limits enforced (API: 512MB/1CPU, Dashboard: 256MB/0.5CPU, Web: 128MB/0.25CPU)

### Container Details

| Service | Dockerfile | Base Image | Port | Healthcheck |
|---------|-----------|------------|------|-------------|
| `api` | `Dockerfile.api` | `python:3.12-slim` | 8000 | `GET /api/health` |
| `dashboard` | `Dockerfile.dashboard` | `python:3.12-slim` | 8001 | `GET /health` |
| `web` | `Dockerfile.web` | `node:20-slim` (build) + `nginx:alpine` (serve) | 80 | `wget http://localhost/` |

All containers run as non-root users with healthcheck intervals of 30 seconds.

## Production Hardening Checklist

### Authentication

- [ ] Generate a strong JWT secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Set `JWT_SECRET_KEY` to the generated value
- [ ] Reduce `JWT_EXPIRE_MINUTES` to 15 or lower
- [ ] Implement real user validation in `POST /api/auth/token` (currently accepts any non-empty credentials)

### CORS

- [ ] Set `CORS_ORIGINS` to your actual domain(s) only
- [ ] Remove `http://localhost:*` origins

### Rate Limiting

- [ ] Set `API_RATE_LIMIT` appropriately (e.g., `60/minute` for production)
- [ ] Consider adding per-endpoint rate limits for search-heavy endpoints

### Database

- [ ] Verify WAL mode is active: `sqlite3 skills.db "PRAGMA journal_mode;"`
- [ ] Set up automated backups via `scripts/backup_db.sh`
- [ ] Configure backup retention with `BACKUP_RETENTION_DAYS` (default: 30)

### Logging

- [ ] Set `SKILL0_LOG_LEVEL=WARNING` in production
- [ ] Keep `SKILL0_LOG_FORMAT=json` for structured log aggregation
- [ ] Configure log shipping to your observability stack

### Network

- [ ] Place behind a reverse proxy (nginx/caddy) with TLS
- [ ] Restrict direct access to API ports
- [ ] Enable HTTPS only

## Health Check Endpoints

| Endpoint | Service | Response |
|----------|---------|----------|
| `GET /health` | Core API | `{"status": "healthy", "db_path": "...", "total_skills": N}` |
| `GET /api/health/detail` | Core API | Detailed: DB size, uptime, embedding model, status |
| `GET /health` | Dashboard API | `{"status": "healthy"}` |

## Troubleshooting

### "sqlite-vec not installed"

```bash
pip install sqlite-vec
```

### "Database not found"

The core API auto-indexes on first startup if `skills.db` is missing. To manually re-index:

```bash
python -m vector_db.search --db skills.db --parsed-dir parsed index
```

### CUDA not available

Set `SKILL0_DEVICE=cpu` to force CPU-only embeddings. The embedder auto-detects GPU availability when set to `auto`.

### Rate limit exceeded (429)

Increase `API_RATE_LIMIT` or wait for the rate window to reset. Default is 100 requests per minute per IP.

### JWT token expired (401)

Request a new token via `POST /api/auth/token` with username and password.
