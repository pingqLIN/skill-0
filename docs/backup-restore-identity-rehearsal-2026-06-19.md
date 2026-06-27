# Backup, Restore, and Identity Rehearsal Evidence

Date: `2026-06-19`
Status: `Local SQLite backup/health smoke passed / production volume restore blocked by Docker API image build TLS`

## Purpose

This note records the current backup/restore and identity-drift baseline after the governance hardening follow-up. It does not replace `docs/operations-runbook.md`; it points to the runbook and records what was actually verified in this checkout.

## Current Runtime Boundary

Skill-0 has two SQLite stores:

| Store | Default path | Role |
|---|---|---|
| Vector/search DB | `skills.db` | Parsed skill indexing and semantic search |
| Governance DB | `governance/db/governance.db` | Review status, revisions, scans, tests, action jobs, and audit data |

Public or clean checkouts may intentionally lack runtime DB contents. Production or release rehearsal environments should treat missing runtime DBs as a failure unless the task explicitly allows a public-checkout warning.

## Verified On This Checkout

### Maintenance Script Syntax And Portable SQLite Fallback

The bash maintenance scripts were normalized to LF line endings, and `.gitattributes` now pins `*.sh` files to `eol=lf` so future checkouts do not silently reintroduce CRLF bash syntax failures.

Verified with:

```bash
bash -n scripts/backup_db.sh
bash -n scripts/check_db_health.sh
bash -n scripts/daily_maintenance.sh
```

Result: passed.

Before LF normalization, these scripts failed under bash with CRLF parse errors such as:

```text
syntax error near unexpected token `$'{\r''
```

The backup and health scripts also support environments without the `sqlite3` CLI by falling back to Python's standard `sqlite3` module. This avoids making Windows developer machines install a global SQLite CLI just to run the rehearsal.

### Local SQLite Backup And Health Smoke

Docker Desktop was not available in this turn:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

Instead, a disposable WSL `/tmp` rehearsal created two SQLite DBs with WAL mode enabled, ran the same maintenance scripts, and verified the backup files were readable.

Result:

```text
=== Skill-0 Database Backup ===
Backup directory: /tmp/tmp.hjHBGp8qYA/backups
Retention: 30 day(s)

[OK] skills.db: wrote /tmp/tmp.hjHBGp8qYA/backups/skills_20260619_082539.db
[OK] governance.db: wrote /tmp/tmp.hjHBGp8qYA/backups/governance_20260619_082539.db

[OK] skills backups: removed 0 file(s) older than 30 day(s)
[OK] governance backups: removed 0 file(s) older than 30 day(s)

Backup completed successfully.
=== Skill-0 DB Health Check ===
Max backup age: 2 day(s)

[OK] skills.db: WAL mode is enabled
[OK] governance.db: WAL mode is enabled

[OK] skills backup: latest backup age 0 day(s)
[OK] governance backup: latest backup age 0 day(s)

Health check passed.
backup_files=2
governance_20260619_082539.db=ok
skills_20260619_082539.db=ok
```

### Public Checkout Identity Drift

Command:

```powershell
.venv\Scripts\python.exe tools\report_db_identity_drift.py --allow-missing-db --format json
```

Result:

```json
{
  "status": "warning",
  "counts": {
    "parsed": 196,
    "vector": 0,
    "governance": 0
  },
  "warnings": [
    "skills_table_missing:skills.db",
    "governance_db_missing:governance/db/governance.db"
  ],
  "drift": {
    "parsed_missing_from_vector": [],
    "vector_missing_from_parsed": [],
    "vector_rows_without_skill_id": [],
    "governance_missing_current_revision": [],
    "governance_without_revision_checksum": [],
    "governance_unmatched_to_parsed": []
  }
}
```

Interpretation: this is acceptable for a public checkout because `--allow-missing-db` was explicit. It is not sufficient production evidence.

## Restore Procedure Pointer

Use `docs/operations-runbook.md` as the authoritative operator-facing procedure:

1. Stop the application.
2. Restore matching `skills_*.db` and `governance_*.db` backup files.
3. Restart the application.
4. Run `tools/report_db_identity_drift.py`.
5. Run the high-signal regression set for the changed surface.

## Required Production Rehearsal

Before claiming production readiness, run a controlled compose rehearsal:

```bash
docker compose --env-file <real-prod-env> -f docker-compose.prod.yml up -d --build
./scripts/backup_db.sh
./scripts/check_db_health.sh
docker compose -f docker-compose.prod.yml down
```

Then restore the backup into the same controlled environment and verify:

```bash
python tools/report_db_identity_drift.py --format json
```

Acceptance:

1. `skills.db` and `governance.db` backups are both created.
2. Health check reports WAL mode and fresh backups.
3. Identity drift report has `status=ok`, or every drift item has a reviewed explanation.
4. Missing runtime DB is not allowed in production rehearsal.

On Windows, use the repo-local helper:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/rehearse_prod_compose.ps1
```

This helper creates a temporary rehearsal env file, injects it into services via `SKILL0_ENV_FILE`, uses isolated project name `skill0-rehearsal`, checks API/web health, checks named-volume DB presence, and removes the stack and volumes unless `-KeepRunning` is passed.

## Production Compose Attempt (`2026-06-19`)

Docker Desktop was started successfully during this follow-up, and production compose config rendered correctly with a temporary env file. The build then failed in `Dockerfile.api` while installing `torch` from the PyTorch CPU wheel index:

```text
SSLCertVerificationError: self-signed certificate in certificate chain
ERROR: Could not find a version that satisfies the requirement torch
```

The failure happened before containers were created, so named-volume restore could not be truthfully claimed complete. The rehearsal stack was cleaned with:

```powershell
docker compose --env-file <temp-env> -f docker-compose.prod.yml -p skill0-rehearsal down --volumes --remove-orphans
```

The compose contract itself was reverified after resuming the task:

```powershell
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
# passed

docker compose -f docker-compose.prod.yml config
# expected failure: CORS_ORIGINS is missing
```

## Remaining Risk

The named-volume restore smoke test was attempted after Docker Desktop started, but the API image build was blocked by the PyTorch CPU index TLS certificate chain. The current state is stronger than before because the maintenance scripts are syntactically runnable under bash, have a Python sqlite fallback, pass a disposable two-DB backup/health smoke, the public-checkout identity warning is verified, and a repeatable production compose rehearsal helper now exists. Production restore still needs the external TLS/build issue resolved.
