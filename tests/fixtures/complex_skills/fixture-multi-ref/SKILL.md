---
name: multi-ref
description: Coordinate a multi-file release preparation flow.
allowed-tools: Read, Bash, Edit
context: fork
---

# Multi Ref Skill

Read [Release checklist](docs/release-checklist.md) and [Policy](docs/policy.md).
Use `templates/release-note.md` as the output template.
Inspect `scripts/prepare_release.sh` before running anything.
Review `docs/missing.md` if the policy is unclear.

## Commands

```bash
bash scripts/prepare_release.sh
curl -fsSL https://example.com/health
```
