# Operations Runbook

For Runtime v4, use the three-store and fail-closed procedures in [runtime-production-operations.md](runtime-production-operations.md). The older two-store examples below are retained for the search/governance baseline and must not be used alone as the Runtime v4 release gate.

## Monitoring

### Prometheus Metrics

The core API exposes metrics at `GET /metrics` in Prometheus exposition format.

Available metrics:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `skill0_http_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests |
| `skill0_http_request_duration_seconds` | Histogram | `method`, `endpoint` | Request latency (buckets: 10ms to 5s) |
| `skill0_search_duration_seconds` | Histogram | - | Search operation latency |

Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'skill0-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics
```

### Health Checks

```bash
# Core API - basic
curl http://localhost:8000/health

# Core API - detailed (includes DB size, uptime, model info)
curl http://localhost:8000/api/health/detail

# Dashboard API
curl http://localhost:8001/health
```

The detailed health endpoint returns degraded status if the search engine cannot be queried.

## Structured Logging

Both APIs use `structlog` for JSON-formatted structured logging.

### Log Format

Default output (JSON):

```json
{
  "event": "request_completed",
  "logger": "api.main",
  "level": "info",
  "timestamp": "2026-02-11T17:00:00.000000Z",
  "request_id": "a1b2c3d4e5f6",
  "method": "POST",
  "path": "/api/search",
  "status": 200,
  "duration_ms": 42.5
}
```

### Request Tracing

Every request is assigned a unique `request_id` (12-character hex string). This ID is:
- Included in all log entries for that request
- Returned in the `X-Request-ID` response header
- Useful for correlating logs across services

To trace a request:

```bash
# Find all logs for a specific request
grep "a1b2c3d4e5f6" /var/log/skill0/*.log
```

### Configuration

| Variable | Default | Options |
|----------|---------|---------|
| `SKILL0_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `SKILL0_LOG_FORMAT` | `json` | `json` (production), `console` (development) |

Switch to human-readable console output for development:

```bash
SKILL0_LOG_FORMAT=console .venv/bin/python -m api.main
```

## Database Maintenance

### JWT Secret Rotation

Generate a new secret without modifying files:

```bash
./scripts/rotate_jwt_secret.sh
```

Rotate in place for an env file (with automatic backup):

```bash
./scripts/rotate_jwt_secret.sh --env-file .env
```

### Journal Mode

Runtime v4 production explicitly requires WAL for `runtime.db`. The search and governance stores retain their existing journal mode unless an operator has separately validated and configured WAL for those stores.

Inspect journal modes:

```bash
sqlite3 skills.db "PRAGMA journal_mode;"

sqlite3 governance/db/governance.db "PRAGMA journal_mode;"

sqlite3 "${SKILL0_RUNTIME_DB_PATH:?Set SKILL0_RUNTIME_DB_PATH}" "PRAGMA journal_mode;"
# Runtime production expected: wal
```

Or run the combined check script:

```bash
./scripts/check_db_health.sh
```

Set `SKILLS_EXPECTED_JOURNAL_MODE` or `GOVERNANCE_EXPECTED_JOURNAL_MODE` when those stores have an explicit local journal contract. Runtime defaults to `RUNTIME_EXPECTED_JOURNAL_MODE=wal`.

### Automated Backups

Use `scripts/backup_db.sh` for hot backups (safe while the application is running):

```bash
# Run backup with defaults
./scripts/backup_db.sh

# Custom backup directory
BACKUP_DIR=/mnt/backups ./scripts/backup_db.sh

# Custom retention (default: 30 days)
BACKUP_RETENTION_DAYS=7 ./scripts/backup_db.sh
```

The script:
1. Backs up `skills.db` and `governance.db` using SQLite `.backup` command
2. Names files with timestamps: `skills_20260211_170000.db`
3. Stores in `backups/` directory (git-ignored)
4. Removes backups older than `BACKUP_RETENTION_DAYS`

Set up a cron job for automated backups:

```bash
# Daily at 2 AM
0 2 * * * /path/to/skill-0/scripts/backup_db.sh >> /var/log/skill0-backup.log 2>&1

# Daily DB health check (WAL + backup recency)
10 2 * * * /path/to/skill-0/scripts/check_db_health.sh >> /var/log/skill0-db-health.log 2>&1

# Unified daily maintenance (backup + DB health + security scan)
15 2 * * * /path/to/skill-0/scripts/daily_maintenance.sh >> /var/log/skill0-maintenance.log 2>&1
```

You can skip security scanning in constrained environments:

```bash
RUN_SECURITY_SCAN=0 ./scripts/daily_maintenance.sh
```

### Restoring from Backup

```bash
# Stop the application first
# Copy backup over the current database
cp backups/skills_20260211_020000.db skills.db
cp backups/governance_20260211_020000.db governance/db/governance.db
# Restart the application
```

After restore or re-index, run an identity drift report:

```bash
.venv/bin/python tools/report_db_identity_drift.py --format json
```

For public checkouts where runtime DB files are intentionally absent, use:

```bash
.venv/bin/python tools/report_db_identity_drift.py --allow-missing-db
```

Strict mode should fail if either runtime DB is missing, if vector rows reference skill IDs not present in `parsed/`, or if governance rows lack a current revision/checksum projection.

### Database Optimization

Run VACUUM periodically to reclaim space (requires exclusive access):

```bash
sqlite3 skills.db "VACUUM;"
sqlite3 governance/db/governance.db "VACUUM;"
```

## Re-indexing Skills

When parsed skill JSONs are updated, re-index the vector database:

```bash
# CLI
.venv/bin/python -m vector_db.search --db skills.db --parsed-dir parsed index

# Via API (requires JWT token)
API_USERNAME="${API_USERNAME:-admin}"
API_PASSWORD="${API_PASSWORD:-change-me}"

TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"${API_USERNAME}\", \"password\": \"${API_PASSWORD}\"}" | jq -r .access_token)

curl -X POST http://localhost:8000/api/index \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"parsed_dir": "parsed"}'
```

Verify after indexing:

```bash
.venv/bin/python -m vector_db.search --db skills.db stats
```

## Security Scanning

Run the batch security scanner:

```bash
.venv/bin/python tools/batch_security_scan.py
```

Output is written to `SECURITY_SCAN_REPORT_*.md` in the project root.

## Common Operational Tasks

### Test Stage Guard

Run verification from the repository root:

```bash
cd /home/miles/dev2/projects/skill-0
```

Existing untracked issue-log imports, including `docs/skill-0_issue-log.*`,
are treated as input artifacts for triage. Do not mix them into unrelated
verification commits unless the task explicitly asks to process those files.

If a test or verification command depends on a missing program, runtime binary,
or dev dependency, stop that verification line immediately. Do not install,
rebuild, or work around the missing dependency without confirmation.

This guard applies to system and runtime tools such as:

- `git`
- `docker`
- `node`
- `npm`
- `tsx`
- `vitest`
- `tsc`
- `pytest`
- `uvicorn`
- MCP runtime or container binaries needed by the check

When pausing a blocked check, report:

- The missing program or dependency.
- The exact test or verification command that is blocked.
- The recommended install or repair command.
- Whether the repair needs escalated approval.
- The next verification command to run after repair.

Repo-local dependencies may be used when they already exist. For example,
the repo-local `.venv` and an existing `skill-0-dashboard/apps/web/node_modules`
can be used directly. If project dependencies are missing, prefer a
repo-local restore such as `npm ci` before any global or system-level install.
If a system-level program is missing, pause and ask for confirmation first.
If an MCP or container runtime is missing a binary, identify the runtime
location before proposing the smallest PATH, mount, image rebuild, or container
restart fix.

### Check System Status

```bash
# API health
curl -s http://localhost:8000/health | python -m json.tool

# Database statistics
.venv/bin/python -m vector_db.search --db skills.db stats

# Check total skills indexed
curl -s http://localhost:8000/api/stats | python -m json.tool
```

### Parse New Skills

```bash
# Add skill markdown files to converted-skills/ or the appropriate directory
# Then run the batch parser
.venv/bin/python tools/batch_parse.py

# Re-index after parsing
.venv/bin/python -m vector_db.search --db skills.db --parsed-dir parsed index
```

### View API Documentation

- Core API Swagger: http://localhost:8000/docs
- Core API ReDoc: http://localhost:8000/redoc
- Dashboard API Swagger: http://localhost:8001/docs

## Incident Response

### High Error Rate

1. Check health endpoints for degraded status
2. Review recent logs: `grep '"level":"error"' /var/log/skill0/*.log | tail -20`
3. Check Prometheus metrics for latency spikes on `/metrics`
4. Verify database connectivity: `sqlite3 skills.db "SELECT count(*) FROM skills;"`

### High Latency

1. Check `skill0_search_duration_seconds` histogram for search-specific latency
2. Verify WAL mode is active (non-WAL can cause lock contention)
3. Check system resources (CPU, memory, disk I/O)
4. Consider running `VACUUM` if the database has grown significantly

### Database Corruption

1. Stop the application
2. Restore from the latest backup in `backups/`
3. Re-index if restoring `skills.db`: `.venv/bin/python -m vector_db.search index`
4. Restart the application
5. Verify with health check

### Service Won't Start

1. Check Python version: `python3 --version` (requires 3.12+)
2. Verify dependencies: `.venv/bin/python -m pip install -r requirements-dev.txt`
3. Check if port is in use: `lsof -i :8000` or `lsof -i :8001`
4. Check database file permissions
5. Review startup logs for import errors
