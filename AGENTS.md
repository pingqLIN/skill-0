# SKILL-0 PROJECT KNOWLEDGE BASE

**Updated:** 2026-04-27
**Branch:** `main`

## Project Guidelines

### Code Style

- Python CLI scripts use `argparse` and write outputs to repo root or `governance/db/` when they persist artifacts.
- Dashboard API uses FastAPI with Pydantic v2 models and mounts routers under `/api`.
- Dashboard web uses React + Tailwind + shadcn/ui patterns, with API clients in `skill-0-dashboard/apps/web/src/api/`.

### Architecture

- Core parser + schema contract + vector search live in `tools/`, `schema/`, `vector_db/`, and `parsed/`.
- Governance is revision-aware and backed by SQLite in `governance/db/governance.db`.
- Dashboard is a monorepo with independent API and web apps under `skill-0-dashboard/apps/`.

### Build and Test

- Activate the repo-local environment first: `source .venv/bin/activate`
- Core API: `.venv/bin/python -m api.main`
- Dashboard API: `cd skill-0-dashboard/apps/api && ../../../.venv/bin/python -m uvicorn main:app --reload --port 8001`
- Dashboard web: `nvm use || nvm install 20.19.0` then `cd skill-0-dashboard/apps/web && npm run dev`
- Python regression: `.venv/bin/python -m pytest tests skill-0-dashboard/apps/api/tests -q`
- Frontend tests/build: `nvm use || nvm install 20.19.0` then `cd skill-0-dashboard/apps/web && npm test && npm run build`

### Project Conventions

- Do not edit `parsed/*.json` manually; regenerate or normalize via tooling.
- Do not commit `skills.db` alongside uncommitted schema/contract drift.
- Treat `schema/skill-decomposition.schema.json` as the live schema source of truth.
- Prefer fidelity wording over strict equivalence wording unless benchmark evidence exists.

## Overview

Skill-0 decomposes Claude Skills and MCP Tools into structured JSON (`actions`, `rules`, `directives`), validates them against the canonical schema, stores embeddings in SQLite-vec, and exposes governance/search surfaces via API and dashboard apps.

## Current Repo Shape

```
skill-0/
├── api/                 # Core FastAPI search/auth API
├── vector_db/           # Embedding + sqlite-vec search engine
├── tools/               # Parsing, validation, governance, normalization scripts
├── parsed/              # 196 checked-in parsed skill JSON files
├── schema/              # Canonical JSON Schema v2.4.0
├── governance/          # Governance DB + policy docs
├── converted-skills/    # 164 imported external skill directories
├── skill-0-dashboard/   # Monorepo: governance API + React web UI
├── docs/                # Review, planning, dossier, and shared-contract docs
└── skills.db            # SQLite + vector store
```

## Where To Look

| Task | Location | Notes |
|------|----------|-------|
| Canonical schema helpers | `tools/schema_contract.py` | Normalization + validation helpers |
| Batch schema validation | `tools/validate_skill_schema.py` | CI-friendly validator |
| Normalize parsed dataset | `tools/normalize_parsed_skills.py` | Backfills legacy shapes to v2.4 |
| Parser generation | `tools/batch_parse.py` | Emits canonicalized parsed JSON |
| Governance DB | `tools/governance_db.py` | Revision-aware governance storage |
| Governance workflow CLI | `tools/skill_governance.py` | Scan/test/approve/reject flow |
| Search logic | `vector_db/search.py` | `SemanticSearch` entrypoint |
| Embeddings | `vector_db/embedder.py` | `all-MiniLM-L6-v2`, CPU/CUDA fallback |
| Dashboard API | `skill-0-dashboard/apps/api/` | JWT-protected governance endpoints |
| Dashboard UI | `skill-0-dashboard/apps/web/` | React 19 + Vite frontend |

## Conventions

- **Schema version**: `2.4.0`
- **ID patterns**: `a_001`, `r_001`, `d_001`
- **skill_id format**: `(claude|mcp)__[scope]__[name]`
- **skill_layer**: `claude_skill`, `mcp_tool`, `mcp_server_internal`
- **Language**: Python 3.12+, Traditional Chinese comments acceptable

## Anti-Patterns

- Never modify `parsed/*.json` by hand.
- Never treat mutable skill rows as the governance source of truth; use revisions.
- Never describe similarity/fidelity scores as strict equivalence without evidence.
- Never rely on dev-only CORS settings in production.

## Commands

```bash
# Schema contract checks
.venv/bin/python tools/validate_skill_schema.py parsed
.venv/bin/python tools/normalize_parsed_skills.py --parsed-dir parsed --write

# Semantic search
.venv/bin/python -m vector_db.search --db skills.db --parsed-dir parsed index
.venv/bin/python -m vector_db.search --db skills.db search "query"
.venv/bin/python -m vector_db.search --db skills.db stats

# Governance
.venv/bin/python tools/skill_governance.py list
.venv/bin/python tools/batch_security_scan.py

# Full regression
.venv/bin/python -m pytest tests skill-0-dashboard/apps/api/tests -q
cd skill-0-dashboard/apps/web && npm test && npm run build
```

## Notes

- `parsed/` currently validates cleanly against the live schema.
- Dashboard auth/session flow is implemented in the web app and backed by JWT endpoints.
- `converted-skills/` is an imported corpus; not all sources are directly parseable by the current analyzer.
