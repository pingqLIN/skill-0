# Governance Authority Gate B Fresh Reapproval Design v1

- Status: **Gate B implemented and independently reviewed for RC; production remains gated by the production security policy**
- Date: `2026-07-21`
- Policy identifier: `governance.fresh-reapproval.v1`
- Prior gate: [`governance-authority-gate-a-design.md`](governance-authority-gate-a-design.md)
- Lifecycle contract: [`contracts/governance-authority-lifecycle-v1.json`](contracts/governance-authority-lifecycle-v1.json)
- Traditional Chinese companion: [`governance-authority-gate-b-design.zh-tw.md`](governance-authority-gate-b-design.zh-tw.md)

## Decision and scope

Gate B adopts the safest no-migration option from Gate A. A rejected current
revision can never be approved directly. Recovery requires a new current
revision, a new exact binding, and scan, equivalence-test, review, and decision
artifacts created for that revision. A fresh packet submitted against the
rejected revision is not an accepted alternative.

This batch does not change the Runtime authority tuple, add a table or column,
perform a physical database migration, add expiry/revocation/quorum, redesign
the Dashboard, enable a real adapter, or alter historical Runtime evidence.
The implementation requires no schema or data migration.

## Mandatory sequence

```text
reject R1
  -> register R2 as pending/unbound
  -> exact runtime_bind for R2 and its canonical artifact digest
  -> non-blocking scan event + row for R2 after binding
  -> passing equivalence-test event + row for R2 after binding
  -> authenticated review event in the approval transaction
  -> approve decision event for R2
```

`approve_skill()` enforces this sequence inside its `BEGIN IMMEDIATE`
transaction. It resolves evidence IDs from server-written audit events; the
caller cannot select scan or test IDs. Each evidence row must match the same
Governance Skill and exact current revision. The binding audit event must carry
the current `artifact_digest`. Missing, failed, blocked, stale, pre-binding, or
cross-revision evidence fails closed without an approval or review event.

The existing authenticated Dashboard route remains compatible: its request
body still contains only `reason`, while the reviewer comes from the JWT
subject. Local CLI callers remain inside the operator boundary; the database
requires a non-empty actor and reason for fresh reapproval.

## Revision reset contract

`register_revision()` preserves historical rows but clears the new revision's:

- artifact binding and approval actor/time;
- scan timestamp/version/risk/findings projections;
- equivalence timestamp/scores/pass projection;
- installed path/time workflow projection; and
- inherited creation time, source checksum, and provenance serialization.

The new revision starts `pending`, `risk_level=unknown`, and unbound. Its source
checksum and provenance are recomputed from the new payload. Prior revisions,
scan/test rows, approval/rejection events, and Runtime history are not changed.

## Review and decision artifacts

For fresh reapproval, the application creates a `review` audit event in the
same transaction as approval. The event records the exact revision, digest,
binding event, scan ID, test ID, reviewer, and reason. The subsequent `approve`
event is the decision artifact and references that review event through the
server-derived `fresh_reapproval` packet.

Initial approval remains backward compatible and does not acquire this
post-rejection packet requirement. Repeated approval of an already approved
current revision retains existing behavior. Identical binding of a rejected
revision remains an idempotent no-op and cannot bypass the direct-reapproval
denial.

The generic revision-state helper cannot approve or reject. Its only allowed
transition is application remediation from `blocked` to `pending`; approval
after that reset requires a new non-blocking scan and passing test recorded
after the reset. Evidence from before the block/reset cannot restore authority.

## Retention and integrity boundary

Application code has no update/delete path for historical revisions,
scan/test evidence, or audit events, and the Gate B workflow only appends new
evidence. Operators must retain those records for at least the associated
Governance and Runtime evidence lifetime and include `governance.db` in the
verified backup/restore policy.

This no-migration batch does **not** provide database-level tamper resistance,
cryptographic chaining, or protection from an out-of-band SQLite writer. Those
remain explicit gaps and require a separately approved persistence design,
migration, recovery rehearsal, and rollback plan. Application append-only
behavior must not be described as physical immutability.

## Verification and rollback

Required checks cover direct-reapproval and generic-state bypass denial with zero side effects,
freshness-state reset, pre-binding evidence rejection, missing/failed evidence,
post-block reset evidence, the positive R1-to-R2 sequence, exact audit references, Runtime denial after
rejection/supersession/drift, existing stale-job behavior, full regression, and
independent review.

Rollback is the inverse code/document commit. It does not delete or rewrite
the additional review/approval audit events created while Gate B is active.
Any unresolved Critical/Warning finding, partial-write behavior, Runtime
authority regression, or claim of database-level immutability is a stop
condition.
