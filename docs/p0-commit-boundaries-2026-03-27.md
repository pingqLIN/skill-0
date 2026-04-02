# P0 Commit Boundaries

Status note: historical process aid. The listed commit boundaries were used to drive the local P0 split on `2026-03-27`; do not treat this file as a current execution plan or open work queue.

Date: `2026-03-27`
Scope: `P0-only local changes`

## Safety Rule

- The current worktree contains many unrelated tracked and untracked changes.
- Do **not** use `git add .` for the P0 batch.
- Stage only the explicit paths below.

## Commit 1

Message:
`p0: enforce immutable governance revisions`

Paths:

```bash
git add \
  tools/governance_db.py \
  tools/backfill_empty_fields.py \
  tools/backfill_governance.py \
  tools/backfill_source_urls.py \
  tools/batch_rescan.py \
  tests/test_governance_revisions.py
```

Why:
- closes in-place revision mutation
- updates backfill/rescan callers to revision-safe behavior
- adds focused regression coverage for governance semantics

## Commit 2

Message:
`p0: align canonical contract and outward-facing versions`

Paths:

```bash
git add \
  tools/schema_contract.py \
  tools/validate_skill_schema.py \
  tools/batch_parse.py \
  scripts/helper.py \
  api/main.py \
  tools/advanced_skill_analyzer.py \
  skill-0-dashboard/apps/api/routers/scans.py \
  tests/test_schema_contract.py \
  tests/test_helper.py \
  tests/integration/test_api_core.py \
  docs/contract-decision.md \
  docs/schema-compatibility-note.md \
  docs/parsed-dataset-validation-report-2026-03-27.md
```

Why:
- centralizes canonical schema/version behavior around `v2.4.0`
- fixes helper/API/analyzer drift
- adds schema-level and API contract regression checks

## Commit 3

Message:
`p0: standardize local python commands on repo venv`

Paths:

```bash
git add \
  vector_db/embedder.py \
  tests/test_embedder.py \
  AGENTS.md \
  README.md \
  README.zh-TW.md \
  tests/README.md \
  docs/deployment-guide.md \
  docs/operations-runbook.md
```

Why:
- makes embedder import/test behavior work without global Python packages
- standardizes current-facing local commands on `.venv/bin/python`
- reduces recurrence of the FastAPI/system-Python mismatch

## Commit 4

Message:
`p0: demote historical docs and close repair plan`

Paths:

```bash
git add \
  reference.md \
  docs/implementation-summary.md \
  docs/document-authority-index-2026-03-27.md \
  docs/p0-repair-plan-2026-03-27.md
```

Optional include if this file is intended to be tracked in this branch:

```bash
git add docs/project-progress-report-2026-03-23.md
```

Why:
- makes archival docs clearly historical at the body level, not only in headers
- introduces a current-vs-historical authority index
- marks the P0 repair plan as locally complete

## Suggested Verification Before Commit 4

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
.venv/bin/python -m pytest \
  tests/test_governance_revisions.py \
  tests/test_schema_contract.py \
  tests/test_helper.py \
  tests/test_embedder.py \
  tests/integration/test_api_core.py \
  skill-0-dashboard/apps/api/tests -q
```
