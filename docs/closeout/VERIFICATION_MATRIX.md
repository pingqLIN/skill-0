# Runtime v4 Closeout Verification Matrix

Baseline phase: `C1 — Reproduce Existing Verification`
Recorded: `2026-07-17T10:11:55+08:00`

## Results

| Gate | Command | Exit | Result | Classification | Evidence |
|---|---|---:|---|---|---|
| Python compile | `python -m compileall api runtime vector_db tools scripts skill-0-dashboard/apps/api -q` | 0 | PASS | — | `evidence/test-results.txt` |
| Doc status | `python tools/check_doc_status_markers.py` | 0 | PASS | — | `evidence/test-results.txt` |
| Shared docs | `python tools/check_shared_docs.py` | 0 | PASS | — | `evidence/test-results.txt` |
| Parsed schema | `python tools/validate_skill_schema.py parsed` | 0 | PASS; 196/196 | — | `evidence/test-results.txt` |
| Runtime-focused tests | focused eight-file pytest command | 0 | PASS; 71 tests | — | `evidence/test-results.txt` |
| Full Python regression | `python -m pytest tests skill-0-dashboard/apps/api/tests -q --timeout=120` | 0 | PASS; 373 tests | 65 `NON_BLOCKING_WARNING` entries | `evidence/test-results.txt` |
| Coverage 75 | full pytest coverage command | 1 | FAIL; 39.99% | `CORE_BLOCKER` | `evidence/coverage.xml`, `evidence/test-results.txt` |
| Frontend dependency restore | `npm ci` | 0 | PASS; 0 vulnerabilities | — | `evidence/web-results.txt` |
| Frontend lint | `npm run lint` | 1 | FAIL; 2 errors | `CORE_BLOCKER` | `evidence/web-results.txt` |
| Frontend tests | `npm test` | 0 | PASS; 34 tests | — | `evidence/web-results.txt` |
| Frontend build | `npm run build:ci` | 0 | PASS; bundle guard passed | — | `evidence/web-results.txt` |
| Docker API image | `docker build -f Dockerfile.api -t skill-0-api:closeout .` | 0 | PASS after daemon start | initial `ENVIRONMENT_BLOCKER` cleared | `evidence/docker-results.txt` |
| Docker Dashboard image | `docker build -f Dockerfile.dashboard -t skill-0-dashboard:closeout .` | 0 | PASS | — | `evidence/docker-results.txt` |
| Docker Web image | `docker build -f Dockerfile.web -t skill-0-web:closeout .` | 0 | PASS | — | `evidence/docker-results.txt` |
| Compose config | `$env:CORS_ORIGINS='https://closeout.invalid'; docker compose -f docker-compose.prod.yml config` | 0 | PASS | required env precondition recorded | `evidence/docker-results.txt` |

## C1 classification

### CORE_BLOCKER

1. Coverage configuration includes the entire `tools` package, including many untested standalone and migration CLIs, producing 39.99% while the configured gate requires 75%. All 373 tests passed in the same run. C2 must repair the gate configuration without weakening Runtime v4 test coverage.
2. Frontend lint reports `react-hooks/set-state-in-effect` in `ReviewQueue.tsx` and `SkillDetail.tsx`. Frontend tests and production build both pass. C2 may make a focused behavior-preserving UI source fix guarded by the existing tests.

### ENVIRONMENT_BLOCKER

- Docker Desktop was installed but its Linux engine was initially stopped. Starting the existing runtime cleared the blocker; all image builds then passed. No installation or Docker configuration change was made.

### NON_BLOCKING_WARNING

- Full Python runs emitted 65 warnings while all 373 tests passed. No warning-only cleanup is authorized.
- Local Node.js is 24.14.1 instead of CI's 20.19.0. Frontend tests and build pass; the Docker Web build uses Node 20.
- Compose config intentionally fails closed when `CORS_ORIGINS` is absent. The recorded gate command supplies a non-secret closeout origin.

## C1 gate decision

`PASS TO C2`: baseline reproduction is complete, every failure is classified, evidence is recorded, and no production source was changed during C1.
