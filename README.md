# Skill-0: Skill Decomposition Parser

[中文版](README.zh-TW.md)

> A ternary classification system for parsing the internal structure of Claude Skills and MCP Tools

## Overview

Skill-0 is a classification system that parses AI/Chatbot Skills (especially Claude Skills and MCP Tools) into structured components.

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
├── README.md                              # English documentation
├── README.zh-TW.md                        # Chinese documentation
├── schema/
│   └── skill-decomposition.schema.json   # JSON Schema v2.0
├── parsed/                                # Parsed skill examples (30 skills)
├── analysis/                              # Analysis reports
├── tools/                                 # Analysis tools
│   ├── analyzer.py                       # Structure analyzer
│   ├── pattern_extractor.py              # Pattern extractor
│   ├── evaluate.py                       # Coverage evaluator
│   └── batch_parse.py                    # Batch parser
└── docs/                                  # Documentation
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

## Statistics (30 Skills)

- **Actions**: 190
- **Rules**: 77
- **Directives**: 107
- **Action Type Coverage**: 100%
- **Directive Type Coverage**: 100%

## Version

- Schema Version: 2.0.0
- Created: 2026-01-23
- Updated: 2026-01-26
- Author: Project Maintainer

## Changelog

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
