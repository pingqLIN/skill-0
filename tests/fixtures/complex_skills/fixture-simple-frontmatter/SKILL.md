---
name: simple-frontmatter
description: Analyze a repository with a manifest-first pass.
allowed-tools: Read, Grep, Bash
context: project
---

# Simple Frontmatter Skill

Use `$ARGUMENTS` to scope the repository under review.

## Workflow

Read `README.md` before making changes.

```bash
rg "TODO|FIXME" .
```
