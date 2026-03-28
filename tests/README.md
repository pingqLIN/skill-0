# Test Suite Documentation

## Current Baseline

This repository currently has two automated regression surfaces:

- Python regression: `17` test files and `178` collected tests across `tests/` and `skill-0-dashboard/apps/api/tests/`
- Frontend smoke/build regression: `18` Vitest tests plus the production bundle guardrail in `skill-0-dashboard/apps/web`

The Python suite is the primary release gate for API, governance, parser, schema, and dashboard-backend behaviour.

## Canonical Commands

### Full Python Regression

```bash
.venv/bin/python -m pytest tests skill-0-dashboard/apps/api/tests -q
```

### High-Signal API Regression

```bash
.venv/bin/python -m pytest tests/integration/test_api_core.py tests/integration/test_auth_flow.py tests/integration/test_rate_limiting.py tests/test_api_security.py skill-0-dashboard/apps/api/tests -q
```

### Schema Contract Validation

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
```

### Frontend Regression

```bash
nvm use || nvm install 20.19.0
cd skill-0-dashboard/apps/web && npm test && npm run build:ci
```

## Test Areas

- `tests/integration/test_api_core.py`: core API search/index/auth surface
- `tests/integration/test_auth_flow.py`: JWT issuance and guarded endpoints
- `tests/integration/test_rate_limiting.py`: API and auth throttling behaviour
- `tests/test_api_security.py`: production config and security guardrails
- `tests/test_schema_contract.py`: canonical schema helpers and parser metadata
- `tests/test_governance_revisions.py`: revision-aware governance invariants
- `tests/test_complex_skill_parser.py`: complex parser fixtures
- `tests/test_embedder.py` / `tests/test_embedder_contract.py`: embedding import/runtime contract
- `skill-0-dashboard/apps/api/tests/`: dashboard API routers, auth, reviews, scans, audit, and stats

## Fixtures

Primary fixtures live under `tests/fixtures/`:

- `valid_skill.json`
- `invalid_skill.json`
- `sample.md`
- `complex_skills/`

Dashboard API tests also use shared fixtures and mock governance services from `skill-0-dashboard/apps/api/tests/conftest.py`.

## Notes

- Run frontend commands only on Node `20.19.x`, which is the CI baseline.
- `parsed/` validation is part of the release contract; do not rely on JSON syntax checks alone.
- Historical test counts in older planning/review docs are snapshots, not the live regression baseline.
