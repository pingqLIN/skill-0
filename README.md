# Skill-0: Skill Decomposition Parser

> A ternary classification system for parsing the internal structure of Claude Skills and MCP Tools

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Schema Version](https://img.shields.io/badge/schema-v2.4.0-green.svg)](schema/skill-decomposition.schema.json)

## Overview

Skill-0 is a classification system that parses AI/Chatbot Skills (especially Claude Skills and MCP Tools) into structured components. It includes **semantic search** powered by vector embeddings for intelligent skill discovery.

## Ternary Classification System

Organizes and defines the immutable parts of a Skill (or parts that change behavior when modified) into three categories:

![Skill Ternary Classification](docs/diagrams/ternary-classification.svg)

| Category | Definition | Characteristics |
|----------|------------|-----------------|
| **Action** | Atomic operation: indivisible basic operation | Deterministic result, no conditional branching, atomic |
| **Rule** | Atomic judgment: pure conditional evaluation/classification | Returns boolean/classification result |
| **Directive** | Descriptive statement: decomposable but chosen not to at this level | Contains completion state, knowledge, principles, constraints, etc. |

### Directive Types

| Type | Description | Example |
|------|-------------|---------|
| `completion` | Completion state description | "All tables extracted" |
| `knowledge` | Domain knowledge | "PDF format specification" |
| `principle` | Guiding principle | "Optimize Context Window" |
| `constraint` | Constraint condition | "Max 25,000 tokens" |
| `preference` | Preference setting | "User prefers JSON format" |
| `strategy` | Strategy guideline | "Retry three times on error" |

### Directive Provenance (Optional)

Skills/Tools may come from diverse sources where the original intent cannot be fully verified. To preserve the original spirit, a `Directive` can optionally include `provenance` in two tiers:

- `basic`: minimal traceability + verbatim excerpt
- `full`: adds location + extraction/translation metadata (backend can encode based on this)

**Basic**

```json
"provenance": {
  "level": "basic",
  "source": { "kind": "mcp_tool", "ref": "example-tool" },
  "original_text": "Prefer concise output"
}
```

**Full**

```json
"provenance": {
  "level": "full",
  "source": { "kind": "claude_skill", "ref": "converted-skills/docx/SKILL.md", "version": "v1" },
  "original_text": "Keep changes minimal",
  "location": { "locator": "SKILL.md#L120" },
  "extraction": { "method": "llm", "inferred": true, "confidence": 0.7 }
}
```

### ID Format

| Element | Pattern | Example |
|---------|---------|---------|
| Action | `a_XXX` | `a_001`, `a_002` |
| Rule | `r_XXX` | `r_001`, `r_002` |
| Directive | `d_XXX` | `d_001`, `d_002` |

## Project Structure

```
skill-0/
├── api/                               # REST API (FastAPI, port 8000)
│   ├── main.py                       # Main API with JWT auth & rate limiting
│   └── logging_config.py            # Structured logging (structlog)
├── vector_db/                         # Vector database module
│   ├── embedder.py                   # Embedding generator (all-MiniLM-L6-v2)
│   ├── vector_store.py               # SQLite-vec storage
│   └── search.py                     # Semantic search engine
├── skill-0-dashboard/                 # Governance Dashboard
│   └── apps/
│       ├── api/                      # Dashboard API (FastAPI, port 8001)
│       └── web/                      # React 19 + Vite frontend
├── governance/                        # Governance system
│   └── db/governance.db              # Skill approval workflow DB
├── schema/                            # JSON Schema v2.4
├── parsed/                            # Parsed skill examples (32 skills)
├── tools/                             # Analysis & governance tools
├── scripts/                           # Maintenance scripts
├── tests/                             # Test suite (111+ tests)
├── docker-compose.yml                 # Development Docker setup
├── docker-compose.prod.yml            # Production Docker setup
├── Dockerfile.{api,dashboard,web}     # Container images
└── skills.db                          # Vector database
```

## Installation

```bash
# Clone the repository
git clone https://github.com/pingqLIN/skill-0.git
cd skill-0

# Install dependencies
pip install -r requirements.txt

# Index skills (first time)
python -m vector_db.search --db skills.db --parsed-dir parsed index
```

## Testing

The project includes a comprehensive test suite with 111+ tests:

```bash
# Run all Python tests
python -m pytest tests/ -v

# Run Dashboard API tests
python -m pytest skill-0-dashboard/apps/api/tests/ -v

# Run frontend tests
cd skill-0-dashboard/apps/web && npm test
```

**Test Coverage**:
- ✅ API security & rate limiting (tests/test_api_security.py)
- ✅ JWT authentication flow (tests/integration/test_auth_flow.py)
- ✅ Rate limiting behavior (tests/integration/test_rate_limiting.py)
- ✅ Dashboard API — all 5 routers (skill-0-dashboard/apps/api/tests/)
- ✅ Frontend smoke tests — 18 component tests (Vitest)
- ✅ Schema validation & format conversion
- ✅ Integration workflows

## REST API

Skill-0 provides two FastAPI servers:

### Main API (port 8000)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/search` | POST/GET | No | Semantic skill search |
| `/api/similar/{name}` | GET | No | Find similar skills |
| `/api/cluster` | GET | No | K-Means clustering |
| `/api/stats` | GET | No | Database statistics |
| `/api/skills` | GET | No | List all skills (paginated) |
| `/api/index` | POST | JWT | Re-index skills |
| `/api/auth/token` | POST | No | Get JWT token |
| `/health` | GET | No | Health check |
| `/metrics` | GET | No | Prometheus metrics |

### Governance Dashboard API (port 8001)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/stats` | GET | JWT | Dashboard statistics |
| `/api/skills` | GET | JWT | Skills with governance status |
| `/api/reviews` | GET | JWT | Pending review queue |
| `/api/scans` | GET | JWT | Security scan results |
| `/api/audit` | GET | JWT | Audit event log |

```bash
# Start both servers
uvicorn api.main:app --port 8000
uvicorn apps.api.main:app --port 8001

# Or use Docker
docker compose up
```

## Semantic Search

Skill-0 includes a powerful semantic search engine powered by `all-MiniLM-L6-v2` embeddings and `SQLite-vec`.

### CLI Commands

```bash
# Index all skills
python -m vector_db.search --db skills.db --parsed-dir parsed index

# Search by natural language
python -m vector_db.search --db skills.db search "PDF document processing"

# Find similar skills
python -m vector_db.search --db skills.db similar "Docx Skill"

# Cluster analysis (auto-grouping)
python -m vector_db.search --db skills.db cluster -n 5

# Show statistics
python -m vector_db.search --db skills.db stats
```

### Search Examples

```bash
$ python -m vector_db.search search "creative design visual art"

🔍 Searching for: creative design visual art
--------------------------------------------------
1. Canvas-Design Skill (53.36%)
2. Theme Factory (46.14%)
3. Anthropic Brand Styling (45.54%)
4. Slack GIF Creator (45.44%)
5. Pptx Skill (45.08%)

Search completed in 72.6ms
```

### Python API

```python
from vector_db import SemanticSearch

# Initialize search engine
search = SemanticSearch(db_path='skills.db')

# Semantic search
results = search.search("PDF processing", limit=5)
for r in results:
    print(f"{r['name']}: {r['similarity']:.2%}")

# Find similar skills
similar = search.find_similar("Docx Skill", limit=5)

# Cluster analysis
clusters = search.cluster_skills(n_clusters=5)
```

## Quick Example

```json
{
  "decomposition": {
    "actions": [
      {
        "id": "a_001",
        "name": "Read PDF",
        "action_type": "io_read",
        "deterministic": true
      }
    ],
    "rules": [
      {
        "id": "r_001",
        "name": "Check File Exists",
        "condition_type": "existence_check",
        "returns": "boolean"
      }
    ],
    "directives": [
      {
        "id": "d_001",
        "name": "PDF Processing Complete",
        "directive_type": "completion",
        "description": "All tables extracted and saved to Excel",
        "decomposable": true
      }
    ]
  }
}
```

## Statistics (32 Skills)

| Metric | Count |
|--------|-------|
| **Skills** | 32 |
| **Actions** | 266 |
| **Rules** | 84 |
| **Directives** | 120 |
| **Action Type Coverage** | 100% |
| **Directive Type Coverage** | 100% |

### Cluster Distribution

| Cluster | Skills | Description |
|---------|--------|-------------|
| 1 | 10 | Development Tools (MCP, Testing) |
| 2 | 5 | Document Processing (PDF, DOCX) |
| 3 | 7 | Creative Design (Canvas, Theme) |
| 4 | 2 | Data Analysis (Excel, Raffle) |
| 5 | 8 | Research Assistant (Leads, Resume) |

## Performance

| Metric | Value |
|--------|-------|
| Index Time | 0.88s (32 skills) |
| Search Latency | ~75ms |
| Embedding Dimension | 384 |
| Database | SQLite-vec |

## Documentation

Comprehensive documentation is available:

- **[CLAUDE.md](CLAUDE.md)** - Best practices for Claude AI integration and skill decomposition
- **[SKILL.md](SKILL.md)** - Complete tool portal and workflow guide
- **[reference.md](reference.md)** - Schema reference and format specifications
- **[examples.md](examples.md)** - 7 detailed skill examples across different domains
- **[AGENTS.md](AGENTS.md)** - Guidelines for AI agents working on this project
- **[scripts/helper.py](scripts/helper.py)** - Helper utilities for validation, conversion, and testing
- **[docs/skill-0-vs-claude-code-simplifier.md](docs/skill-0-vs-claude-code-simplifier.md)** - Comparison with Claude Code Simplifier (EN)
- **[docs/skill-0-vs-claude-code-simplifier.zh-TW.md](docs/skill-0-vs-claude-code-simplifier.zh-TW.md)** - 與 Claude Code Simplifier 比較 (zh-TW)

### Quick Start Guide

```bash
# Generate a new skill template
python scripts/helper.py template -o my-skill.json

# Convert markdown to skill JSON
python scripts/helper.py convert skill.md my-skill.json

# Validate skill against schema
python scripts/helper.py validate my-skill.json

# Test execution paths
python scripts/helper.py test my-skill.json --analyze
```

See [docs/helper-test-results.md](docs/helper-test-results.md) for detailed test results and examples.

## Version

- Schema Version: 2.4.0
- Created: 2026-01-23
- Updated: 2026-02-26
- Author: pingqLIN

## Changelog

### v2.4.0 (2026-02-26) - Security, Testing & Production Readiness
- **Security**: JWT authentication for both API servers
- **Security**: Rate limiting with per-endpoint controls
- **Security**: CORS environment variable configuration
- **Security**: Production security enforcement (fail-fast on misconfiguration)
- **Monitoring**: Prometheus metrics endpoint (`/metrics`)
- **Monitoring**: Structured logging with structlog (JSON/console output)
- **Testing**: 79 new tests (111+ total) — Dashboard API, auth flow, rate limiting, frontend
- **DevOps**: Docker containerization (3 Dockerfiles + docker-compose)
- **DevOps**: CI/CD pipeline with pytest-cov, web build, Docker build verification
- **Tools**: Vector DB sync script with governance cross-reference
- **Schema**: v2.4.0 with Hive-inspired features (quality signals, success criteria, failure patterns)

### v2.3.0 (2026-01-28) - Testing & Quality Assurance
- **New Feature**: Comprehensive automated test suite
  - 32 tests covering all helper utilities
  - Tool equivalence verification (validator consistency)
  - Code equivalence verification (converter determinism)
  - Integration workflow testing
  - Error handling and edge case coverage
- Test fixtures and documentation in `tests/`
- pytest configuration in `pyproject.toml`
- CI/CD ready test infrastructure

### v2.2.0 (2026-01-28) - Documentation & Tooling
- **New Feature**: Comprehensive documentation suite
  - `CLAUDE.md` - Claude best practices guide
  - `SKILL.md` - Complete tool portal and workflow
  - `reference.md` - Full schema reference
  - `examples.md` - 7 detailed skill examples
  - `AGENTS.md` - AI agent guidelines
- **New Tool**: `scripts/helper.py` - Utility for validation, conversion, and testing
  - Template generation
  - Markdown to JSON conversion
  - Schema validation
  - Execution path testing
  - Complexity analysis
- Integration with agents.md format standard
- Test results documentation in `docs/helper-test-results.md`

### v2.1.0 (2026-01-26) - Stage 2
- **New Feature**: Semantic search with vector embeddings
  - `vector_db` module with SQLite-vec integration
  - `all-MiniLM-L6-v2` embedding model (384 dimensions)
  - K-Means clustering for skill grouping
  - CLI tool: `python -m vector_db.search`
- Expanded to 32 skills (+21 from awesome-claude-skills)
- Performance: 0.88s indexing, ~75ms search

### v2.0.0 (2026-01-26)
- **Breaking Change**: Redefined ternary classification
  - `core_action` → `action` (ID: `ca_XXX` → `a_XXX`)
  - `mission` → `directive` (ID: `m_XXX` → `d_XXX`)
- Added `directive_type` support: completion, knowledge, principle, constraint, preference, strategy
- Added `decomposable` and `decomposition_hint` fields
- Added `action_type`: `await_input`
- Schema structure optimization
- Added 19 new skills from ComposioHQ/awesome-claude-skills

### v1.1.0 (2026-01-23)
- Initial version

## License

MIT
