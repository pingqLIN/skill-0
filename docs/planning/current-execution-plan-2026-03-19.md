# Skill-0 Current Execution Plan

Updated: `2026-03-19`

## Current state

- `skill-0` has been restored as a clean clone from `origin/main`.
- `UniText` has been recovered into its own directory at `<unitext-root>`.
- Core API and dashboard API test suites now run together without Python package/import collisions.
- Core API integration tests no longer dirty the tracked `skills.db`; tests use an isolated temporary DB copy.
- Frontend dependency audit is clean after lockfile-only fixes.
- Frontend production build no longer emits the large-chunk warning after route/chart code splitting.
- The repo now has a repeatable Python dev dependency entrypoint via `requirements-dev.txt`.
- CI now matches the current local baseline more closely: combined Python regression, web lint/test/build, and cached embedding model warm-up.

## Verified baseline

- Python regression: `157 passed`
  - Command: `python -m pytest tests skill-0-dashboard/apps/api/tests -q`
  - Result: warning-free after test environment cleanup
- Python dev install: passed
  - Command: `python -m pip install -r requirements-dev.txt`
- Dashboard web tests: `18 passed`
  - Command: `npm test`
- Dashboard web lint: passed
  - Command: `npm run lint`
- Dashboard web production build: passed
  - Command: `npm run build`
- Dashboard web CI build guardrail: passed
  - Command: `npm run build:ci`
- Frontend install: `npm ci` passed
- Frontend audit: `0 vulnerabilities`
  - Command: `npm audit --json`

## Changes completed in this execution round

1. Restored clean `skill-0` and recovered `UniText` into separate folders.
2. Updated dashboard API tests to match current JWT-protected behavior and current `ActionResult` contract.
3. Fixed dashboard/core test namespace collision by:
   - switching governance tests to `apps.api.*` imports
   - adding `skill-0-dashboard/apps/__init__.py`
4. Fixed dashboard test auth token generation so it respects the active `JWT_SECRET_KEY`.
5. Isolated core integration tests from the tracked `skills.db`.
6. Cleared frontend audit findings via safe lockfile updates.
7. Split the frontend bundle with lazy-loaded routes and a deferred `recharts` dashboard chart.
8. Added `requirements-dev.txt` so the repo can bootstrap its own Python environment independent of the recovered `UniText` virtualenv.
9. Updated CI to use the unified Python dependency set, run combined Python regression, run frontend tests, and warm/cache the `all-MiniLM-L6-v2` embedding model on CPU.
10. Reduced Python test warning noise to zero by:
   - using 32+ byte JWT test secrets
   - forcing CPU mode in the Python test environment
   - replacing deprecated `datetime.utcnow()` calls in `scripts/helper.py`
11. Added a frontend bundle-size guardrail script and wired CI to use `npm run build:ci`.

## Highest-value next items

### 1. Repo-local bootstrap convenience

- `requirements-dev.txt` is enough for reproducibility, but setup is still manual.
- Goal: add a small bootstrap script or Make target if repeated local onboarding friction shows up.

### 2. Optional bundle reporting

- CI now enforces a bundle-size ceiling, but it does not emit a visual breakdown artifact.
- Goal: add a lightweight report artifact only if bundle analysis becomes a recurring task.

## Execution order

1. Add extra local bootstrap convenience only if the current setup still feels too manual.
2. Add optional bundle reporting only if size regressions need deeper analysis.
