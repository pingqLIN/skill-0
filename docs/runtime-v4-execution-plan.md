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
| E | Production storage, deadlines, doctor, backup/restore/restart rehearsal and release gate | 365 Python/API tests, 34 web tests, production build, full three-store Compose rehearsal, independent reviewer | `1021d8e`, `c95f2b3` |
| F | Single-adapter certification contract and fail-closed production admission | Seven isolated probes plus focused Runtime regression; human production approval pending | `8e24d61` |

## Batch E work packages

1. Persist `runtime.db` separately and mount `governance.db` read-only into Core API.
2. Enforce production WAL, binding-key separation, explicit decision actors, and bounded HITL TTL.
3. Expire pending and approved-but-unconsumed HITL items without mutating historical decisions.
4. Extend backup and health workflows from two stores to three.
5. Add a read-only production doctor and backup-aware release gate.
6. Rehearse three-store backup/restore validity and Core API restart persistence in an isolated Compose project.
7. Run full backend/frontend regression, production build, static Compose checks, and independent review.

## Release decision

Runtime v4 passed operator acceptance and the controlled internal dry-run pilot on 2026-07-17. The full production image build and isolated Compose rehearsal verified service health, the production doctor, all three SQLite stores, online backup/restore, and Runtime persistence across an API restart. The final regression passed 365 Python/API tests, 34 web tests, the production web build, and all 196 canonical schema validations.

This result is not authorization for real external writes. Batch F now defines those controls for the single `skill0.local-pdf-filesystem` candidate: credential-free least privilege, end-to-end idempotency-key delivery, reconciliation, recoverable compensation evidence, rate limiting, and signed per-adapter/per-environment production admission. The technical certification passes, but no human production approval has been issued.

Batch F verification passes 373 Python/API tests, 34 web tests, the production web build, all 196 canonical schema validations, and seven isolated adapter probes.

## Production Admission Phase 1 completion

Phase 1 of the Production Admission implementation is complete as of
2026-07-21. Commit `167f23f` adds the signed, exact-release-bound,
fail-closed admission package verifier, its schema, operator handoff and
recovery documentation, and direct regression coverage.

The completion gate passed 16 focused admission tests, the full 571-test
Python/API regression suite, frontend lint, 36 frontend tests, the production
web build, and the bundle-size guard. The canonical parsed corpus also remains
subject to the repository schema validation gate.

This completion statement covers the Phase 1 contract, verifier, documentation,
and test surface only. Production Admission remains
`WAITING_FOR_OPERATOR_EVIDENCE`: no real operator evidence, environment-specific
human approval, credential, external write, service start, deployment, or
public exposure was used or authorized by this validation.

## Internal pilot outcome and next step

The controlled pilot used the canonical PDF skill's `a_006` file-creation action with a test adapter and `dry_run=true`:

1. The exact parsed artifact was bound to the current governance revision and approved.
2. The bounded-write action paused at an action-scoped approval; a Dashboard decision was recorded and the same run was explicitly resumed to `succeeded` with an 11-event evidence stream.
3. A process-local clock advance projected a second approval as expired; the decision was rejected and no decision record was persisted.
4. A simulated timeout after `action_started` produced `action_outcome_unknown` and `reconciliation_required` without automatic retry.
5. Evidence and operator observations were archived locally in an ignored audit artifact. No real adapter, external credential, or external write was enabled.

The certification contract and isolated candidate are now implemented. See [adapter-certification.md](adapter-certification.md). The next gate is an environment-specific human approval with OS identity and ACL evidence, followed by a separately approved loader/rehearsal batch. Until then, `/api/runs` remains test-adapter-only and `dry_run=true`.
