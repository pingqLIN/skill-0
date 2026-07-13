---
name: skill0-arde-runtime
description: Implement or review SKILL-0 ARD runtime contracts, append-only effect ledgers, dry-run policy gates, compensation recovery, and Evidence projections while preserving the existing Action/Rule/Directive decomposition.
---

# SKILL-0 ARD Runtime Governance

Use this repository-scoped skill for work involving `skill-runtime-contract.schema.json`, `runtime/`, runtime migrations, recovery tests, governed adapters, or Evidence projections.

## Required sequence

1. Read the nearest `AGENTS.md` and the approved ExecPlan.
2. Confirm `audit/v4-phase0/repo-baseline.json` matches the current `git rev-parse HEAD` or explicitly refresh the audit.
3. Read `docs/ADR-0004-ard-plus-evidence.md`, `docs/ADR-0005-event-ledger.md`, and `docs/ADR-0006-runtime-boundary.md`.
4. Preserve the semantic invariants in `references/semantic-invariants.md`.
5. Make one issue-sized, reversible change.
6. Run focused tests, failure-injection tests, and the repository regression suite.
7. Record validation evidence and unresolved risks in the ExecPlan.

## Fail-closed rules

- Do not evaluate arbitrary code or expressions from Skill documents.
- Do not enable real execution by default.
- Do not treat semantic similarity as authorization or safe replay.
- Do not report rollback success without a terminal ledger event.
- Do not use framework checkpoints as evidence that an external effect was reversed.
- Stop and escalate when a write effect lacks durable identity, idempotency, or a recovery path.

## Review

Use `references/review-gates.md` before marking an issue complete.
