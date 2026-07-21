# Governance Authority Lifecycle Decision Proposal v1

- Status: **Partially implemented through Gates A/B; remaining proposals grant no implementation authority**
- Date: `2026-07-20`
- Current lifecycle: [`governance-authority-lifecycle.md`](governance-authority-lifecycle.md)
- Runtime boundary: [`ADR-0006-runtime-boundary.md`](ADR-0006-runtime-boundary.md)
- Traditional Chinese companion: [`governance-authority-lifecycle-proposal.zh-tw.md`](governance-authority-lifecycle-proposal.zh-tw.md)

## Purpose

This proposal turns the documented Governance authority gaps into explicit
operator decisions. It does not change Runtime admission, add an Asset type,
enable a resolver or real adapter, alter Dashboard scope, or authorize a
physical database migration.

The current authority unit remains the exact current approved revision, bound
canonical Asset identity, matching artifact digest, approver, and approval
timestamp. Runtime create and resume continue to revalidate that tuple.

## Decision boundary

The following remain unimplemented controls: approval expiry, a dedicated
append-only revocation decision, quorum/separation of duties, and a
cryptographic Governance audit chain. They must remain documented as gaps until
an approved implementation closes them. Gates A and B implement current-target
enforcement and fresh reapproval without a schema migration.

| Decision | Candidate direction | Current consequence | Separate authority needed |
|---|---|---|---|
| Current-target enforcement | Enforce the captured current target for approve/reject/scan/test writes. | **Implemented in Gate A:** stale jobs fail without evidence/projection writes and cannot retry. | Complete; extensions require a new focused review. |
| Fresh reapproval | Require a new exact bind plus revision-scoped scan/test/review/decision evidence after rejection. | **Implemented in Gate B:** direct rejected-revision approval is denied; database-level tamper resistance remains absent. | Complete for application enforcement; physical immutability requires a separate persistence gate. |
| Approval expiry | Attach an explicit expiry rule to an approval and fail Runtime admission after it. | Approval has no renewal clock. | Time semantics, operator policy, and persistence design. |
| Revocation | Add a dedicated, append-only revocation decision that ends current authority without rewriting history. | Rejection, blocking, supersession, or drift are the available effects. | Incident authority and persistence design. |
| Quorum / separation of duties | Require distinct authenticated roles for bind, evidence review, approval, and emergency revocation. | Actor separation is deployment policy only. | Identity-source and role-governance decision. |
| Audit chain | Bind Governance decisions into a verifiable chain while retaining the existing Runtime ledger boundary. | `audit_log` is not cryptographically chained. | Retention, key custody, and migration design. |

## Required operator decisions

Before implementation, an authorized operator must decide and record:

1. Which lifecycle changes are required for the next release boundary, and
   which remain deferred.
2. The expiry policy: no expiry, fixed duration, risk-tier duration, or an
   explicit renewal workflow; including clock source and behavior during clock
   uncertainty.
3. Who may approve, revoke, or override an approval; whether emergency
   revocation needs one actor or quorum; and the separation-of-duties rule.
4. What exact evidence must be fresh for reapproval and its retention period.
5. Whether persistence changes are allowed. A data-model change requires a
   separately approved migration plan, backup/restore rehearsal, and rollback
   procedure; this proposal grants none of those.

An absent decision is `UNKNOWN`, not permission to relax Runtime admission or
silently retain authority.

## Recommended sequencing

### Gate A — compatibility-only design

Produce a file-scoped design for current-target enforcement and reapproval
preconditions. It must show that every affected API operation still preserves
the current exact-authority tuple, immutable Runtime events, and read-only Core
access to `governance.db`. Do not implement it in this proposal.

The reviewed design artifact is
[`governance-authority-gate-a-design.md`](governance-authority-gate-a-design.md).
It records the implemented current-target enforcement contract but leaves
fresh-evidence semantics at Gate B because the required evidence and retention
rules are not yet chosen.

### Gate B — authority semantics decision

The implemented decision is recorded in
[`governance-authority-gate-b-design.md`](governance-authority-gate-b-design.md).
It selects mandatory new-revision fresh evidence for reapproval and explicitly
defers expiry, revocation, quorum, cryptographic chaining, and physical
immutability.

### Gate C — migration and recovery decision

If Gate B needs new persisted lifecycle facts, prepare a separate migration
proposal. It must define a staged copy, integrity checks, backup/restore,
current-revision reconciliation, backward-compatibility behavior, and rollback.
No physical migration may begin until that proposal is independently approved.

### Gate D — implementation batches

Only after the above decisions, split implementation by authority capability:
current-target enforcement; fresh reapproval; expiry; revocation; quorum; and
audit chain. Each batch needs focused negative tests, Runtime create/resume
tests, independent review, and its own reversible commit.

## Non-negotiable invariants

- Action, Rule, and Directive remain the only decomposition categories; Evidence
  remains orthogonal.
- The current exact Governance revision and artifact digest remain Runtime
  admission authority; Search, Dashboard, Knowledge, Evaluation, and mutable
  projections do not become authority.
- Existing Runtime events and decision history remain append-only and are never
  rewritten to simulate revocation, renewal, or continuity.
- Runtime HITL approval remains separate from Governance authority.
- The system remains `asset_type=skill`, dry-run-only, single-host, and
  three-store. This proposal does not authorize FTS5 integration, a Dashboard
  redesign, a new Asset type, a real adapter, or a database migration.

## Acceptance evidence for a future implementation

A future accepted batch must provide:

1. exact before/after authority-state and audit-event tests, including stale,
   non-current, rejected, blocked, drifted, and expired cases;
2. Runtime create and resume denial tests after every authority-ending event;
3. failure-injection evidence proving no partial authority grant survives a
   crash or retry;
4. backup/restore and doctor evidence if any stored state changes;
5. an independent review with no unresolved Critical or Warning finding; and
6. an explicit statement of unsupported legacy records and rollback behavior.

Until those conditions are met, the lifecycle document and Production Security
Policy remain the authoritative description of current behavior and gaps.
