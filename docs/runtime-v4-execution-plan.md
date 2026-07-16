# Runtime v4 Execution Plan

This document is the authoritative implementation and handoff plan for Runtime v4. See [runtime-v4-execution-plan.zh-tw.md](runtime-v4-execution-plan.zh-tw.md) for the Traditional Chinese companion.

## Outcome

Runtime v4 turns the existing ARD/runtime contract into a truthful, dry-run-only execution surface with deterministic evidence, durable human approval, exact governance admission, and a fail-closed production operating contract. Real side-effecting adapters remain outside this plan.

## Delivered batches

| Batch | Scope | Acceptance evidence | Commit |
|---|---|---|---|
| A | Truthful run creation; test adapters and `dry_run=true` only | Runtime contract/API tests | `58b2c06` |
| B | Deterministic event/evidence projection | Evidence schema and replay tests | `c7b7ce3` |
| C | Durable action-scoped HITL, same-run resume, recovery/reconciliation | Concurrency, crash-gap, immutable decision tests | `ae2ec39` |
| D | Exact current-revision governance admission and Runtime dashboard | 356 Python/API tests, 34 web tests, production build, independent reviewer | `5c8e7ee` |
| E | Production storage, deadlines, doctor, backup/restore/restart rehearsal and release gate | 365 Python/API tests, 34 web tests, production build, Compose config, WSL three-store restore rehearsal, independent reviewer | This commit |

## Batch E work packages

1. Persist `runtime.db` separately and mount `governance.db` read-only into Core API.
2. Enforce production WAL, binding-key separation, explicit decision actors, and bounded HITL TTL.
3. Expire pending and approved-but-unconsumed HITL items without mutating historical decisions.
4. Extend backup and health workflows from two stores to three.
5. Add a read-only production doctor and backup-aware release gate.
6. Rehearse three-store backup/restore validity and Core API restart persistence in an isolated Compose project.
7. Run full backend/frontend regression, production build, static Compose checks, and independent review.

## Release decision

Runtime v4 is ready for an internal dry-run pilot when Batch E passes. It is not authorization for real external writes. A later adapter-certification batch must separately define credentials, least privilege, idempotency semantics, reconciliation probes, compensation evidence, rate limits, and per-adapter production approval.

The full container build/rehearsal remains an operator acceptance item because this verification environment had no reusable Skill-0 images and downloading new image/dependency layers was outside the authorized boundary. Compose rendering, script parsing, the local three-store rehearsal, and reviewer gate passed; do not represent the unrun container build as completed.

## Recommended next step after Batch E

Run one controlled internal pilot using a single canonical skill and test adapter:

1. Bind the exact parsed artifact to the current governance revision and approve it.
2. Create a dry run that pauses at one action approval.
3. Record a Dashboard decision, wait briefly, explicitly resume the same run, and inspect evidence.
4. Repeat once with an expired approval and once with a simulated ambiguous outcome.
5. Archive the evidence summary and operator observations; do not enable a real adapter yet.

The next engineering proposal should be adapter certification, not broader autonomous execution.
