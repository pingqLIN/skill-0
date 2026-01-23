# Skill-0: MCP Skill Decomposition Parser

> A general classification program for parsing Claude Skills and MCP Tools into structured components.

## Overview

Skill-0 is a classification system for parsing the internal component structure of AI/Chatbot Skills (especially Claude Skills and MCP Tools).

## Ternary Classification System

The immutable/change-affecting parts within a Skill are organized and classified as:

| Classification | Definition | Characteristics |
|------|------|------|
| **Core Action** | Core action: basic operations without judgment value system | Deterministic execution results, no conditional branches, atomic operations |
| **Rules** | Pure judgment: classification discussion without actions | Returns boolean/classification results, conditional evaluation |
| **Mission** | Task/work: the ultimate goal direction | Combines multiple Actions + Rules, has clear output but serves as a stopping condition without internal analysis |

## Project Structure

```
skill-0/
├── README.md
├── schema/
│   └── skill-decomposition.schema.json    # JSON Schema specification
├── parsed/
│   ├── skill-0-parser.json                # Parser self-parsing
│   ├── mcp-echo.json                      # MCP echo tool parsing
│   ├── mcp-get-current-time.json          # MCP time tool parsing
│   └── mcp-get-sum.json                   # MCP sum tool parsing
└── docs/
    └── conversation-2026-01-23.md         # Original conversation record
```

## Version

- Schema Version: 1.1.0
- Created: 2026-01-23
- Author: pingqLIN

## License

MIT

---

**Note:** This documentation is machine translated. Please refer to [README_zh-tw.md](README_zh-tw.md) for the original Chinese content.
