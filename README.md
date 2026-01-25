# Skill-0: MCP Skill Decomposition Parser

> A general classification program for parsing Claude Skills and MCP Tools into structured components.

## Overview

Skill-0 is a classification system used to parse the internal component structure of AI/Chatbot Skills (especially Claude Skills and MCP Tools).

## Ternary Classification System

The immutable parts of a Skill—or parts that change the behavior if modified—are organized and defined as:

| Category | Definition | Characteristics |
|------|------|------|
| **Core Action** | Core actions: foundational operations that do not carry judgment value systems | Deterministic results, unconditional branching, atomic operations |
| **Rules** | Pure judgment: discusses classification without actions | Returns boolean/classification results, condition evaluation |
| **Mission** | Tasks/works: the final target direction | Combines multiple Actions + Rules, has a clear output, but serves as a stopping condition and is not analyzed internally here |

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
