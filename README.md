# Skill-0: Skill Decomposition Parser

[中文版](README.zh-TW.md)

> A ternary classification system for parsing the internal structure of Claude Skills and MCP Tools

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Schema Version](https://img.shields.io/badge/schema-v2.2.0-green.svg)](schema/skill-decomposition.schema.json)

## Overview

Skill-0 is a classification system that parses AI/Chatbot Skills (especially Claude Skills and MCP Tools) into structured components. It includes **semantic search** powered by vector embeddings for intelligent skill discovery.

## Ternary Classification System

Organizes and defines the immutable parts of a Skill (or parts that change behavior when modified) into three categories:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/skill-ternary-classification.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/images/skill-ternary-classification.svg">
  <img alt="Skill Ternary Classification Diagram" src="docs/images/skill-ternary-classification.svg" width="800">
</picture>


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

>

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

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/project-structure.svg">
  <source media="(prefers-color-scheme: light)" srcset="docs/images/project-structure.svg">
  <img alt="Skill-0 Project Structure" src="docs/images/project-structure.svg" width="600">
</picture>

> 

## Installation

```bash
# Clone the repository
git clone https://github.com/pingqLIN/skill-0.git
cd skill-0

# Install dependencies
pip install -r requirements.txt

# Index skills (first time)
python -m src.vector_db.search --db db/skills.db --parsed-dir data/parsed index
```

## Testing

The project includes a comprehensive test suite for tool and code equivalence verification:

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test categories
python3 -m pytest tests/test_helper.py::TestSkillValidator -v
python3 -m pytest tests/test_helper.py::TestIntegrationWorkflows -v
```

**Test Coverage**: 32 tests covering:

- ✅ Schema validation (tool equivalence)
- ✅ Format conversion (code equivalence)
- ✅ Execution path testing
- ✅ Template generation
- ✅ Error handling
- ✅ Integration workflows

See [tests/README.md](tests/README.md) for detailed test documentation.

## Semantic Search

Skill-0 includes a powerful semantic search engine powered by `all-MiniLM-L6-v2` embeddings and `SQLite-vec`.

### CLI Commands

```bash
# Index all skills
python -m src.vector_db.search --db db/skills.db --parsed-dir data/parsed index

# Search by natural language
python -m src.vector_db.search --db db/skills.db search "PDF document processing"

# Find similar skills
python -m src.vector_db.search --db db/skills.db similar "Docx Skill"

# Cluster analysis (auto-grouping)
python -m src.vector_db.search --db db/skills.db cluster -n 5

# Show statistics
python -m src.vector_db.search --db db/skills.db stats
```

### Search Examples

```bash
$ python -m src.vector_db.search search "creative design visual art"

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
from src.vector_db import SemanticSearch

# Initialize search engine
search = SemanticSearch(db_path='db/skills.db')

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
- **[reference.md](docs/guides/reference.md)** - Schema reference and format specifications
- **[examples.md](docs/guides/examples.md)** - 7 detailed skill examples across different domains
- **[AGENTS.md](AGENTS.md)** - Guidelines for AI agents working on this project
- **[scripts/helper.py](src/tools/helper.py)** - Helper utilities for validation, conversion, and testing

### Agent-Lightning Inspired Enhancements ⚡

Skill-0 now includes architectural patterns inspired by Microsoft's [Agent-Lightning](https://github.com/microsoft/agent-lightning) project:

- **[agent-lightning-comparison.md](docs/agent-lightning-comparison.md)** - Comprehensive technical comparison between the two projects
- **[agent-lightning-enhancements.md](docs/agent-lightning-enhancements.md)** - Usage guide for new distributed features
- **Coordination Layer** - Central hub for distributed task management (like LightningStore)
- **Parser Abstraction** - Unified interface for different parsing strategies (like Algorithm abstraction)
- **Worker Pool** - Parallel execution of skill processing tasks (like Runners)

**Quick Example - Distributed Parsing**:
```python
from src.coordination import SkillStore, SkillWorker
from src.parsers import AdvancedSkillParser

# Initialize coordination store
store = SkillStore(db_path="db/coordination.db")

# Enqueue tasks
for skill_path in skill_files:
    await store.enqueue_parse_task(skill_path)

# Create worker pool (4 parallel workers)
parser = AdvancedSkillParser()
workers = [SkillWorker(f"worker-{i}", store, parser) for i in range(4)]

# Process in parallel - 4x speedup!
await asyncio.gather(*[w.run() for w in workers])
```

See [examples/distributed_parsing.py](examples/distributed_parsing.py) for a complete working example.

### Quick Start Guide

```bash
# Generate a new skill template
python src/tools/helper.py template -o my-skill.json

# Convert markdown to skill JSON
python src/tools/helper.py convert skill.md my-skill.json

# Validate skill against schema
python src/tools/helper.py validate my-skill.json

# Test execution paths
python src/tools/helper.py test my-skill.json --analyze
```

See [docs/helper-test-results.md](docs/helper-test-results.md) for detailed test results and examples.

## Version

- Schema Version: 2.2.0
- Project Version: 2.5.0
- Created: 2026-01-23
- Updated: 2026-02-02
- Author: pingqLIN

## Changelog

### v2.5.0 (2026-02-02) - Agent-Lightning Inspired Enhancements ⚡

- **New Feature**: Distributed skill processing architecture inspired by [Microsoft Agent-Lightning](https://github.com/microsoft/agent-lightning)
  - **Coordination Layer** (`src/coordination/`): Central SkillStore hub for task management
  - **Parser Abstraction** (`src/parsers/`): Unified SkillParser interface for extensibility  
  - **Worker Pool**: Parallel execution with SkillWorker for 4x speedup
- **Technical Comparison**: 17KB comprehensive analysis document comparing Agent-Lightning and Skill-0 architectures
- **Documentation**: Usage guide and working examples for distributed parsing
- **Test Suite**: 9 comprehensive tests validating all new components (100% passing)
- **Performance**: 4x faster parallel processing with 4 workers
- **Scalability**: Foundation for distributed, horizontal scaling

### v2.4.0 (2026-01-30) - GitHub Skills Discovery & Resource Dependencies
- **Schema Update**: v2.1.0 → v2.2.0
  - Added `resource_dependency` definition type with 8 resource categories
  - Resources can be defined at meta (global) and action levels
  - Support for database, API, filesystem, GPU, memory, credentials, network, environment
  - Includes specification details, fallback strategies, and required flags
- **GitHub Skills Search**: Discovered 75+ repositories aligning with skill-0 goals
  - Top 30 projects documented (MCP servers, Claude skills, AI frameworks)
  - MCP ecosystem: 4,509 repositories found
  - Top repository: awesome-mcp-servers (79,994 ⭐)
  - License analysis and compatibility verification
- **New Documentation**:
  - `docs/github-skills-search-report.md` - Comprehensive search report
  - `docs/github-skills-search-results.json` - Structured project data
  - `examples/database-query-analyzer-with-resources.json` - Resource example
  - `tools/github_skill_search.py` - GitHub search utility

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

## Related Projects

### Hue-Sync: LG OLED TV Smart Lighting Sync Application

**Note**: The LG OLED TV Hue Sync project documentation has been moved to a separate repository for better organization.

📦 **Files Moved**: 3 documentation files (~66.5KB) related to developing a Philips Hue Sync-like smart lighting application for LG OLED TVs.

📚 **Transfer Documentation**: See [docs/TRANSFER_TO_HUE_SYNC_REPO.md](docs/TRANSFER_TO_HUE_SYNC_REPO.md) for:
- Complete file list and metadata
- Step-by-step transfer instructions (bilingual)
- Recommended repository structure
- Sample README content

🚀 **Quick Reference**: [docs/QUICK_REFERENCE_HUE_SYNC_TRANSFER.md](docs/QUICK_REFERENCE_HUE_SYNC_TRANSFER.md)

**Status**: Documentation complete, ready for manual repository creation and file transfer.

---

## License

MIT
