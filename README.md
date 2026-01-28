# Skill-0: Skill Decomposition Parser

> A ternary classification system for parsing the internal structure of Claude Skills and MCP Tools

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Schema Version](https://img.shields.io/badge/schema-v2.0.0-green.svg)](schema/skill-decomposition.schema.json)

## Overview

Skill-0 is a classification system that parses AI/Chatbot Skills (especially Claude Skills and MCP Tools) into structured components. It includes **semantic search** powered by vector embeddings for intelligent skill discovery.

## Ternary Classification System

Organizes and defines the immutable parts of a Skill (or parts that change behavior when modified) into three categories:

```
┌─────────────────────────────────────────────────────────────┐
│              Skill Ternary Classification                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐   │
│  │   Action    │   │    Rule     │   │   Directive     │   │
│  ├─────────────┤   ├─────────────┤   ├─────────────────┤   │
│  │ Atomic ops  │   │ Atomic      │   │ Descriptive     │   │
│  │ Indivisible │   │ judgment    │   │ statements      │   │
│  │             │   │ Indivisible │   │ Decomposable    │   │
│  │ Answers:    │   │ Answers:    │   │ but paused      │   │
│  │ "What to do"│   │"How to judge│   │                 │   │
│  └─────────────┘   └─────────────┘   └─────────────────┘   │
│        │                 │                    │             │
│        ▼                 ▼                    ▼             │
│   🔒 Terminal       🔒 Terminal        ⏸️ Pause point      │
│                                        (can deep parse)    │
└─────────────────────────────────────────────────────────────┘
```

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

### ID Format

| Element | Pattern | Example |
|---------|---------|---------|
| Action | `a_XXX` | `a_001`, `a_002` |
| Rule | `r_XXX` | `r_001`, `r_002` |
| Directive | `d_XXX` | `d_001`, `d_002` |

## Project Structure

```
skill-0/
├── README.md                              # Documentation
├── schema/
│   └── skill-decomposition.schema.json   # JSON Schema v2.0
├── parsed/                                # Parsed skill examples (32 skills)
├── analysis/                              # Analysis reports
├── tools/                                 # Analysis tools
│   ├── analyzer.py                       # Structure analyzer
│   ├── pattern_extractor.py              # Pattern extractor
│   ├── evaluate.py                       # Coverage evaluator
│   └── batch_parse.py                    # Batch parser
├── vector_db/                             # Vector database module
│   ├── embedder.py                       # Embedding generator
│   ├── vector_store.py                   # SQLite-vec storage
│   └── search.py                         # Semantic search CLI
├── monitor/                               # Moltbot Monitor Extension (NEW)
│   ├── risk_classifier.py                # Risk assessment engine
│   ├── sequence_analyzer.py              # Command sequence analysis
│   ├── alert_manager.py                  # Real-time alert system
│   ├── risk_logger.py                    # Risk logging system
│   └── monitor_engine.py                 # Main monitor engine
├── skills.db                              # Vector database
└── docs/                                  # Documentation
```

## Installation

```bash
# Clone the repository
git clone https://github.com/<owner>/skill-0.git
cd skill-0

# Install dependencies
pip install sqlite-vec sentence-transformers scikit-learn

# Index skills (first time)
python -m vector_db.search --db skills.db --parsed-dir parsed index
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

## Moltbot Monitor Extension

A lightweight real-time supervision program for Moltbot using Skill-0's ternary classification technology.

### Quick Start

```python
from monitor import MoltbotMonitor, CommandInput, RiskLevel

# Create monitor
monitor = MoltbotMonitor()

# Check command risk
command = CommandInput(
    command_id='cmd_001',
    command_name='delete_files',
    actions=[{'action_type': 'io_write', 'name': 'Delete', 'description': 'Delete files'}]
)

result = monitor.check_command(command)
if not result.is_safe:
    print(f"Blocked: {result.block_reason}")
```

### Features

- **Risk Classification**: Assess command risk based on action types
- **Sequence Analysis**: Detect dangerous command patterns (data exfiltration, privilege escalation)
- **Real-time Alerts**: Immediate notifications for critical threats
- **Risk Logging**: Comprehensive audit trail

See [monitor/README.md](monitor/README.md) for full documentation.

## Version

- Schema Version: 2.0.0
- Created: 2026-01-23
- Updated: 2026-01-28
- Author: Project Maintainer

## Changelog

### v2.2.0 (2026-01-28) - Moltbot Monitor
- **New Feature**: Moltbot Monitor Extension
  - `monitor` module for real-time command supervision
  - Risk classification engine based on Skill-0 action types
  - Sequence pattern analysis for detecting dangerous command chains
  - Alert management with async processing
  - Comprehensive risk logging system
  - 22 unit tests with 100% pass rate

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
