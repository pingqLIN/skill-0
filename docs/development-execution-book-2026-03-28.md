# Development Execution Book — 2026-03-28

## Baseline

- Audit baseline: `origin/main` after merge commit `466a70a` (`#115`)
- Working branch for this execution round: `audit-main-2026-03-28`
- Validation environment:
  - Python: repo-local `.venv`
  - Frontend: `skill-0-dashboard/apps/web`

## What Was Reviewed

This round performed a parallel audit across four areas:

1. Python/backend/runtime and deployment
2. Dashboard API/web correctness
3. Current-facing documentation and contributor commands
4. Repo hygiene, CI, and release invariants

## Implemented In This Round

### 1. Review Attribution Integrity

Problem:
- The dashboard review API trusted a client-supplied `reviewer` field.
- The web client hardcoded every review action as `admin`.

Changes:
- Review requests now accept only `reason`
- Reviewer identity is derived from the validated JWT `sub`
- Extra request fields are rejected
- API tests were updated to assert server-derived attribution

Files:
- `skill-0-dashboard/apps/api/routers/reviews.py`
- `skill-0-dashboard/apps/api/schemas/review.py`
- `skill-0-dashboard/apps/api/tests/test_reviews.py`
- `skill-0-dashboard/apps/web/src/api/reviews.ts`

### 2. Scan Export HTML Correctness

Problem:
- `format=html` returned JSON containing an HTML string instead of a true HTML response.
- The governance spec link in the export payload pointed to a placeholder repository URL.

Changes:
- HTML exports now return `HTMLResponse`
- Exported reports now reference the real governance document URL
- Scan export tests now cover HTML responses

Files:
- `skill-0-dashboard/apps/api/routers/scans.py`
- `skill-0-dashboard/apps/api/tests/test_scans.py`

### 3. Production API First-Boot Hardening

Problem:
- The production API image baked `skills.db` into `/app/data`, but `docker-compose.prod.yml` mounted a named volume over that path.
- On first boot, the container could start against an empty volume and never seed the search DB.

Changes:
- Added an API container entrypoint that seeds the runtime DB from an image-baked bootstrap copy when the runtime DB is missing
- Wired the entrypoint into `Dockerfile.api`
- Moved the baked seed DB to `/app/bootstrap/skills.db`

Files:
- `Dockerfile.api`
- `scripts/docker-entrypoint-api.sh`

### 4. CI Contract Enforcement

Problem:
- CI only checked JSON syntax, not parsed corpus/schema contract validity.

Changes:
- Added `python tools/validate_skill_schema.py parsed` to the `validate-json` job

Files:
- `.github/workflows/ci.yml`

### 5. Current-Facing Documentation Repair

Problem:
- Dashboard API startup commands pointed to the wrong virtualenv path
- Web commands lacked a clear Node baseline
- `tests/README.md` still described the pre-P0 `32 tests` state
- Production env example did not match actual container paths

Changes:
- Fixed Dashboard API startup commands to use the repo-root `.venv`
- Added Node `20.19.0` baseline guidance where contributors run frontend commands
- Rewrote `tests/README.md` around the current regression entrypoints
- Updated `.env.production.example` to match container paths used by `docker-compose.prod.yml`

Files:
- `AGENTS.md`
- `README.md`
- `README.zh-TW.md`
- `docs/deployment-guide.md`
- `tests/README.md`
- `.env.production.example`

## Verified In This Round

### Completed Checks

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
.venv/bin/python -m pytest tests skill-0-dashboard/apps/api/tests -q
cd skill-0-dashboard/apps/web && npm test && npm run build:ci
.venv/bin/python -m pytest skill-0-dashboard/apps/api/tests/test_reviews.py skill-0-dashboard/apps/api/tests/test_scans.py -q
```

Observed results:
- Parsed corpus validation: `195 passed, 0 failed`
- Python regression: `178 passed`
- Frontend tests: `18 passed`
- Frontend build and bundle guardrail: passed
- Narrow reviews/scans API tests: `11 passed`

### In Progress / Expensive Verification

- `docker build -f Dockerfile.api -t skill-0-api:audit .`
  - Used to verify the new API entrypoint wiring
  - If this fails, the likely regression surface is `Dockerfile.api` or the entrypoint script permissions/path

## Remaining High-Signal Backlog

### High

1. Dashboard pages still turn backend failures into empty or zero-value success states.
   - Affected surfaces include dashboard stats, review queue, skills list, and audit log.
   - Next action: add explicit `isError` UI states and query-failure tests.

2. Current repo docs still contain many absolute `/home/miles/...` links in historical review/report material.
   - Next action: convert current-facing docs and authority indices to portable relative links.

### Medium

1. `requirements.lock` is not used by CI, Docker, or bootstrap docs, but still looks like an authority file.
   - Next action: either wire it into a real lock workflow or archive/remove it.

2. Mutable runtime artifacts remain part of repo history (`skills.db`, backup DBs, generated reports).
   - Next action: define which of these are real seed artifacts and move the rest to ignored artifact storage.

3. Production env and deployment docs are improved, but should still be audited as a complete operator runbook after the Docker bootstrap change lands.

## Recommended Next Execution Order

1. Merge the review/scans/deploy/docs fixes from this round
2. Add explicit dashboard error-state rendering and frontend tests
3. Clean up authority drift in current-facing docs
4. Decide the fate of `requirements.lock`, tracked DB artifacts, and generated reports

## Merge Readiness

This batch is ready for review once the API Docker build confirms the new entrypoint wiring. The highest-risk functional issues identified at the start of the audit are either fixed in this branch or clearly isolated in the remaining backlog above.
