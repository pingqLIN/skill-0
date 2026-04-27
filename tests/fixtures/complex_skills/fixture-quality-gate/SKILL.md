---
name: fixture-quality-gate
description: Fixture for fidelity gate coverage across references, commands, and known failure notes.
policy: docs/source-policy.md
---
# Fixture Quality Gate

Use [source policy](docs/source-policy.md) before accepting imported skill content.
Render output with `templates/report.md`.
Load optional settings from `configs/review.yaml`.
The old migration note at `docs/missing-legacy-note.md` is intentionally absent.

## Commands

```bash
curl https://example.com/skills/feed.json
rg "fidelity" docs/source-policy.md
```

## Known Failure Notes

The parser should flag the unresolved legacy note and classify the network command
as review-required evidence. This fixture is a fidelity gate, not strict equivalence
proof.
