# Skill-0 Document Authority

Updated: `2026-07-18`

This page is the current document entry point. The Runtime v4 closeout remains
feature-frozen. The explicitly approved P0 Runtime Asset plan opens an additive
post-closeout milestone without changing the Runtime v4 release boundary.

## Current authority

Read in this order:

1. [`../README.md`](../README.md) — product scope and supported Runtime v4 boundary.
2. [`runtime-architecture-v1.md`](runtime-architecture-v1.md) — accepted Runtime Asset stable-foundation architecture and change boundary.
3. [`planning/runtime-asset-foundation-next-round-plan.md`](planning/runtime-asset-foundation-next-round-plan.md) — implemented P0 Runtime Asset execution authority and scope gates.
4. [`planning/runtime-asset-p0-1-operational-readiness-plan.md`](planning/runtime-asset-p0-1-operational-readiness-plan.md) — implemented P0.1 identity and operator-readiness work.
5. [`planning/runtime-asset-p1-search-evidence-plan.md`](planning/runtime-asset-p1-search-evidence-plan.md) — completed offline-only FTS5 plus sqlite-vec evidence gate; no production integration authority.
6. [`../ai-context-export/CURRENT_STATE.md`](../ai-context-export/CURRENT_STATE.md) — compact frozen Runtime v4 state and branch handoff.
7. [`closeout/FINAL_REPORT.md`](closeout/FINAL_REPORT.md) — Runtime v4 release decision, exact verification, and rollback.
8. [`runtime-production-operations.md`](runtime-production-operations.md) — three-store production operations.
9. [`operations-runbook.md`](operations-runbook.md) — operator commands and incident workflow.
10. [`closeout/VERIFICATION_MATRIX.md`](closeout/VERIFICATION_MATRIX.md) — command-level Runtime v4 acceptance evidence.

The non-suffixed English operations documents are authoritative. Existing `.zh-tw.md` companions are human-readable translations.

## Supporting contracts

- [`knowledge-plane-extension-contract.md`](knowledge-plane-extension-contract.md) defines context-only, Directive-bound Knowledge Plane extensions without adding an Asset type or authority source.
- [`agent-evaluation-benchmark-framework.md`](agent-evaluation-benchmark-framework.md) defines deterministic, replay-based evaluation evidence and freeze gates without provider execution.
- [`runtime-v4-execution-plan.md`](runtime-v4-execution-plan.md) records the implemented Runtime v4 architecture but does not reopen the frozen feature scope.
- [`runtime-v4-contract.md`](runtime-v4-contract.md) and [`runtime-v4-contract.json`](runtime-v4-contract.json) define the runtime contract.
- [`shared-documentation-model.md`](shared-documentation-model.md) and [`gui-governance.md`](gui-governance.md) define the external GUI mirror boundary.
- [`closeout/KNOWN_LIMITATIONS.md`](closeout/KNOWN_LIMITATIONS.md) and [`closeout/DEFERRED_BACKLOG.md`](closeout/DEFERRED_BACKLOG.md) separate accepted limitations from future work.
- [`reports/runtime-asset-p0-verification-and-p1-decision.md`](reports/runtime-asset-p0-verification-and-p1-decision.md) records the verified P0 result and evidence-gated P1 NO-GO decisions.
- [`reports/runtime-asset-p0-1-operational-readiness.md`](reports/runtime-asset-p0-1-operational-readiness.md) records canonical identity repair, guarded local Index creation, backups, and the remaining Governance authority boundary.
- [`reports/runtime-asset-p1-search-evidence.md`](reports/runtime-asset-p1-search-evidence.md) records the reviewed 84-query FTS5/sqlite-vec evidence run and its `NO_GO` decision.

## Historical material

Date-named plans, development reports, old final-phase documents, and [`document-authority-index-2026-03-27.md`](document-authority-index-2026-03-27.md) are historical evidence unless a current-authority document links them for a specific fact. They must not be used to expand the closeout scope.

## External and mirrored material

The `skill-0-GUI` repository is a separately governed companion. Mirror drift or external service availability is not a Core Runtime blocker unless the current release authority explicitly promotes it.
