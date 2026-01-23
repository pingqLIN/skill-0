# Skill-0: MCP Skill Decomposition Parser

> A general classification program for parsing Claude Skills and MCP Tools into structured components.

## Overview

Skill-0 is a classification system for parsing the internal component structure of AI/Chatbot Skills (specifically Claude Skills and MCP Tools).

## Ternary Classification System

The immutable parts of a Skill or parts whose modification will cause effect changes are organized and classified as:

| Classification | Definition | Characteristics |
|------|------|------|
| **Core Action** | Core action: basic operations without judgment or value system | Deterministic execution results, no conditional branches, atomic operations |
| **Rules** | Pure judgment: classification discussion without actions | Returns boolean/classification results, conditional evaluation |
| **Mission** | Task/work: the final goal direction | Combines multiple Actions + Rules, has clear output |

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
    └── conversation-2026-01-23.md         # Original conversation log
```

## Version

- Schema Version: 1.1.0
- Created: 2026-01-23
- Author: pingqLIN

## License

MIT

---

*This is a machine translation. For the original content, please refer to the file named 'README_zh-tw.md'.*
