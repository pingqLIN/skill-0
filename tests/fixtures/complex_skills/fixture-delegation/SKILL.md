---
name: delegation-skill
description: Split review work across the main reviewer and explorer agent.
allowed-tools: Read, Bash
context: fork
agent: explorer
---

# Delegation Skill

Delegate supporting evidence collection to `subskills/evidence.md`.
Use the explorer subagent to inspect `configs/scan.toml`.

## Commands

```bash
python scripts/collect_evidence.py --quick
```
