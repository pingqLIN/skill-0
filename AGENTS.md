<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
# SKILL-0 PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-28
**Commit:** 9d9de81
**Branch:** main

# Project Guidelines

## Code Style

- Python CLI scripts use `argparse` and write outputs to repo root or `governance/db/` (see `tools/AGENTS.md`).
- Dashboard API uses FastAPI with Pydantic v2 models and `/api` router prefix (see `skill-0-dashboard/apps/api/AGENTS.md`).
- Dashboard web uses React + Tailwind + shadcn/ui, `cn()` for class merging, and API base URL in `src/api/client.ts` (see `skill-0-dashboard/apps/web/AGENTS.md`).

## Architecture

- Core parser + vector search live in `tools/`, `vector_db/`, `schema/`, and `parsed/` (see Overview below).
- Governance dashboard is a monorepo with separate API and web apps under `skill-0-dashboard/apps/`.

## Build and Test

- API server: `python -m api.main` (core API) and `cd skill-0-dashboard/apps/api && uvicorn main:app --reload --port 8001` (dashboard API).
- Web dev server: `cd skill-0-dashboard/apps/web && npm run dev`.
- Tests: `python3 -m pytest tests/ -v` (see `tests/README.md`).

## Project Conventions

- Do not edit `parsed/*.json` manually; regenerate with `tools/batch_parse.py`.
- Do not commit `skills.db` with uncommitted schema changes.
- Dashboard API and web are independent; no shared dependencies (see `skill-0-dashboard/AGENTS.md`).

## Integration Points

- Vector search uses `skills.db` and `vector_db/` (see `vector_db/search.py`).
- Dashboard API reads parent `skills.db` via relative path; web proxies API in dev (see `skill-0-dashboard/AGENTS.md`).

## Security

- Security scanning entry point: `tools/batch_security_scan.py`; findings go to `SECURITY_SCAN_REPORT_*.md`.
- CORS in dashboard API is `allow_origins=["*"]` for dev only; lock down for prod.

## OVERVIEW

Claude Skills & MCP Tools decomposition parser with semantic search. Parses skill definitions into structured JSON (Actions/Rules/Directives), stores in SQLite with vector embeddings for similarity search.

## STRUCTURE

```
skill-0/
├── api/                 # FastAPI semantic search API (port 8000)
├── vector_db/           # Embedding + sqlite-vec search engine
├── tools/               # CLI utilities (parsing, scanning, governance)
├── parsed/              # Output: 32 decomposed skill JSONs
├── schema/              # JSON Schema v2.1 definition
├── governance/          # Security scan policies
├── converted-skills/    # 171 imported skills from external sources
├── skill-0-dashboard/   # Monorepo: React dashboard + FastAPI governance API
├── analysis/            # Parser evaluation reports
└── skills.db            # SQLite + vector store (~1.8MB)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new skill parser | `tools/batch_parse.py` | Uses `advanced_skill_analyzer.py` |
| Modify search logic | `vector_db/search.py` | `SemanticSearch` class |
| Change embedding model | `vector_db/embedder.py` | Default: `all-MiniLM-L6-v2` |
| Update JSON schema | `schema/skill-decomposition.schema.json` | v2.1 format |
| Run security scan | `tools/batch_security_scan.py` | Outputs to `SECURITY_SCAN_REPORT_*.md` |
| Governance workflow | `tools/skill_governance.py` | Approval/review flow |
| Dashboard API | `skill-0-dashboard/apps/api/` | FastAPI governance endpoints |
| Dashboard UI | `skill-0-dashboard/apps/web/` | React + Vite + TailwindCSS |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `SemanticSearch` | class | `vector_db/search.py` | Main search interface |
| `VectorStore` | class | `vector_db/vector_store.py` | SQLite + sqlite-vec |
| `SkillEmbedder` | class | `vector_db/embedder.py` | sentence-transformers |
| `app` | FastAPI | `api/main.py` | REST API v2.1 |
| `app` | FastAPI | `skill-0-dashboard/apps/api/main.py` | Governance API v1.0 |

## CONVENTIONS

- **Schema version**: 2.1.0 (see `schema/skill-decomposition.schema.json`)
- **ID patterns**: `a_001` (action), `r_001` (rule), `d_001` (directive)
- **skill_id format**: `(claude|mcp)__[server]__[name]`
- **skill_layer**: `claude_skill`, `mcp_tool`, `mcp_server_internal`
- **Language**: Python 3.12+, Comments in 中文 (Traditional Chinese) acceptable

## ANTI-PATTERNS (THIS PROJECT)

- Never modify `parsed/*.json` manually — regenerate via `tools/batch_parse.py`
- Never commit `skills.db` with uncommitted schema changes
- CORS is `allow_origins=["*"]` for dev only — restrict in production

## COMMANDS

```bash
# Semantic search CLI
python -m vector_db.search index          # Index all parsed skills
python -m vector_db.search search "query" # Search skills
python -m vector_db.search stats          # Show statistics

# API server
python -m api.main                        # Start REST API (port 8000)

# Batch operations
python tools/batch_parse.py               # Parse skills to JSON
python tools/batch_security_scan.py       # Run security scans
python tools/batch_import.py              # Import external skills

# Dashboard (monorepo)
cd skill-0-dashboard/apps/api && uvicorn main:app --reload  # API
cd skill-0-dashboard/apps/web && npm run dev                # Frontend
```

## NOTES

- `converted-skills/` contains 171 imported skills from GitHub Copilot instructions — not parseable by current analyzer
- Vector search uses L2 distance, converted to similarity as `1/(1+distance)`
- Dashboard is a separate monorepo with its own package management
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
# SKILL-0 PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-28
**Commit:** 9d9de81
**Branch:** main

## OVERVIEW

Claude Skills & MCP Tools decomposition parser with semantic search. Parses skill definitions into structured JSON (Actions/Rules/Directives), stores in SQLite with vector embeddings for similarity search.

## STRUCTURE

```
skill-0/
├── api/                 # FastAPI semantic search API (port 8000)
├── vector_db/           # Embedding + sqlite-vec search engine
├── tools/               # CLI utilities (parsing, scanning, governance)
├── parsed/              # Output: 32 decomposed skill JSONs
├── schema/              # JSON Schema v2.1 definition
├── governance/          # Security scan policies
├── converted-skills/    # 171 imported skills from external sources
├── skill-0-dashboard/   # Monorepo: React dashboard + FastAPI governance API
├── analysis/            # Parser evaluation reports
└── skills.db            # SQLite + vector store (~1.8MB)
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Add new skill parser | `tools/batch_parse.py` | Uses `advanced_skill_analyzer.py` |
| Modify search logic | `vector_db/search.py` | `SemanticSearch` class |
| Change embedding model | `vector_db/embedder.py` | Default: `all-MiniLM-L6-v2` |
| Update JSON schema | `schema/skill-decomposition.schema.json` | v2.1 format |
| Run security scan | `tools/batch_security_scan.py` | Outputs to `SECURITY_SCAN_REPORT_*.md` |
| Governance workflow | `tools/skill_governance.py` | Approval/review flow |
| Dashboard API | `skill-0-dashboard/apps/api/` | FastAPI governance endpoints |
| Dashboard UI | `skill-0-dashboard/apps/web/` | React + Vite + TailwindCSS |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `SemanticSearch` | class | `vector_db/search.py` | Main search interface |
| `VectorStore` | class | `vector_db/vector_store.py` | SQLite + sqlite-vec |
| `SkillEmbedder` | class | `vector_db/embedder.py` | sentence-transformers |
| `app` | FastAPI | `api/main.py` | REST API v2.1 |
| `app` | FastAPI | `skill-0-dashboard/apps/api/main.py` | Governance API v1.0 |

## CONVENTIONS

- **Schema version**: 2.1.0 (see `schema/skill-decomposition.schema.json`)
- **ID patterns**: `a_001` (action), `r_001` (rule), `d_001` (directive)
- **skill_id format**: `(claude|mcp)__[server]__[name]`
- **skill_layer**: `claude_skill`, `mcp_tool`, `mcp_server_internal`
- **Language**: Python 3.12+, Comments in 中文 (Traditional Chinese) acceptable

## ANTI-PATTERNS (THIS PROJECT)

- Never modify `parsed/*.json` manually — regenerate via `tools/batch_parse.py`
- Never commit `skills.db` with uncommitted schema changes
- CORS is `allow_origins=["*"]` for dev only — restrict in production

## COMMANDS

```bash
# Semantic search CLI
python -m vector_db.search index          # Index all parsed skills
python -m vector_db.search search "query" # Search skills
python -m vector_db.search stats          # Show statistics

# API server
python -m api.main                        # Start REST API (port 8000)

# Batch operations
python tools/batch_parse.py               # Parse skills to JSON
python tools/batch_security_scan.py       # Run security scans
python tools/batch_import.py              # Import external skills

# Dashboard (monorepo)
cd skill-0-dashboard/apps/api && uvicorn main:app --reload  # API
cd skill-0-dashboard/apps/web && npm run dev                # Frontend
```

## NOTES

- `converted-skills/` contains 171 imported skills from GitHub Copilot instructions — not parseable by current analyzer
- Vector search uses L2 distance, converted to similarity as `1/(1+distance)`
- Dashboard is a separate monorepo with its own package management
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
