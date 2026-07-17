# Skill-0 Document Authority

Updated: `2026-07-17`

This page is the current document entry point. The Runtime v4 closeout is feature-frozen; dated planning files do not become current merely because they describe unfinished work.

## Current authority

Read in this order:

1. [`../README.md`](../README.md) — product scope and supported Runtime v4 boundary.
2. [`../ai-context-export/CURRENT_STATE.md`](../ai-context-export/CURRENT_STATE.md) — compact current state and branch handoff.
3. [`closeout/FINAL_REPORT.md`](closeout/FINAL_REPORT.md) — release decision, exact verification, and rollback.
4. [`runtime-production-operations.md`](runtime-production-operations.md) — three-store production operations.
5. [`operations-runbook.md`](operations-runbook.md) — operator commands and incident workflow.
6. [`closeout/VERIFICATION_MATRIX.md`](closeout/VERIFICATION_MATRIX.md) — command-level acceptance evidence.

The non-suffixed English operations documents are authoritative. Existing `.zh-tw.md` companions are human-readable translations.

## Supporting contracts

- [`runtime-v4-execution-plan.md`](runtime-v4-execution-plan.md) records the implemented Runtime v4 architecture but does not reopen the frozen feature scope.
- [`runtime-v4-contract.md`](runtime-v4-contract.md) and [`runtime-v4-contract.json`](runtime-v4-contract.json) define the runtime contract.
- [`shared-documentation-model.md`](shared-documentation-model.md) and [`gui-governance.md`](gui-governance.md) define the external GUI mirror boundary.
- [`closeout/KNOWN_LIMITATIONS.md`](closeout/KNOWN_LIMITATIONS.md) and [`closeout/DEFERRED_BACKLOG.md`](closeout/DEFERRED_BACKLOG.md) separate accepted limitations from future work.

## Historical material

Date-named plans, development reports, old final-phase documents, and [`document-authority-index-2026-03-27.md`](document-authority-index-2026-03-27.md) are historical evidence unless a current-authority document links them for a specific fact. They must not be used to expand the closeout scope.

## External and mirrored material

The `skill-0-GUI` repository is a separately governed companion. Mirror drift or external service availability is not a Core Runtime blocker unless the current release authority explicitly promotes it.
