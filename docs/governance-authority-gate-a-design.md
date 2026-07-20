# Governance Authority Gate A Compatibility Design v1

- Status: **A1 implemented and independently reviewed**
- Date: `2026-07-20`
- Follow-on: [`governance-authority-gate-b-design.md`](governance-authority-gate-b-design.md) implements the no-migration fresh-reapproval decision as of `2026-07-21`.
- Decision proposal: [`governance-authority-lifecycle-proposal.md`](governance-authority-lifecycle-proposal.md)
- Current behavior: [`governance-authority-lifecycle.md`](governance-authority-lifecycle.md)
- Traditional Chinese companion: [`governance-authority-gate-a-design.zh-tw.md`](governance-authority-gate-a-design.zh-tw.md)

## Purpose and boundary

This Gate A artifact defines and records the compatibility-only implementation
of current-target enforcement, while preserving the unresolved decisions for
fresh reapproval. It does not alter the authority tuple, change Runtime
admission, add an Asset type, redesign the Dashboard, or permit a physical
database migration.

The exact current approved Governance revision and matching canonical identity,
artifact digest, version, approver, and approval timestamp remain the only
Runtime authority. Mutable projections, jobs, scans, Search, Knowledge, and
Evaluation remain non-authoritative.

## Historical pre-A1 baseline

- `approve_skill()` rejects an explicitly supplied non-current revision.
- `reject_skill()` and `record_security_scan()` accept an explicit historical
  revision and may change `skills.status` without changing current Runtime
  authority.
- Dashboard action jobs capture `target_revision_id`, but scan execution reads
  the then-current revision instead of enforcing the captured target. A retry
  retains the captured identifier.
- A rejected current revision can be approved again without a new binding or a
  defined fresh-evidence packet.
- Runtime create and resume independently revalidate current exact authority;
  historical Runtime events remain append-only.

## A1 — current-target enforcement

### Database boundary

Add one private resolver in `tools/governance_db.py`, used inside the same write
transaction as the affected operation:

```python
_require_current_revision(
    connection,
    *,
    skill_id: str,
    revision_id: str | None,
) -> sqlite3.Row
```

An omitted `revision_id` resolves to `skills.current_revision_id`, preserving
legacy callers. An explicit identifier must equal the current identifier. A
missing skill, missing current revision, or stale explicit target fails before
any revision row, mutable projection, scan result, or audit event is written.

The implementation uses the resolver from `approve_skill()`, `reject_skill()`,
`record_security_scan()`, and `record_equivalence_test()`. Evidence writers
raise a stable `GovernanceTargetError`; boolean approval/rejection callers keep
their existing `False` failure contract.

### Dashboard job boundary

The action worker passes the immutable job `target_revision_id` through
`run_scan()` or `run_test()` into the matching evidence writer. If a new
revision supersedes that target before or during execution, the job fails as
`STALE_TARGET_REVISION`; it does not retarget, update projections, or emit
successful scan/test evidence. The error is non-retriable. An operator must
enqueue a new job for the new current revision.

Existing synchronous callers that omit `revision_id` retain current behavior.
Evidence writes expose the stable domain error; action jobs expose its stable
structured error code. HTTP routes require no new request field.

### Candidate files

| File | Intended change |
|---|---|
| `tools/governance_db.py` | Transaction-local current-target resolver for approve, reject, scan, and equivalence writes. |
| `skill-0-dashboard/apps/api/services/governance.py` | Pass captured target through scan/test execution; fail stale jobs without retargeting. |
| `skill-0-dashboard/apps/api/routers/skills.py` | Only if required to normalize a stale-target response; no UI redesign. |
| `tests/test_governance_revisions.py` | Negative DB tests for stale reject/scan/test and zero side effects. |
| `skill-0-dashboard/apps/api/tests/test_governance.py` | Superseded queued-job and retry tests. |
| `tests/test_runtime_api.py` | Preserve create/resume denial and exact-authority revalidation coverage. |
| Lifecycle docs and JSON contract | Update only in the same implementation commit that changes verified behavior. |

## A2 — fresh reapproval preconditions

Gate A does not fully specify or authorize fresh reapproval. `decision_evidence`
is optional audit detail, identical binding is intentionally idempotent, and a
new revision currently inherits scan/test projections. Those facts cannot prove
freshness without an operator-defined evidence contract.

The safest no-migration candidate is to deny direct approval of a rejected
current revision and require a new revision, an exact new binding, and evidence
created for that revision before approval. Gate B must first decide:

1. which scan, test, review, and decision artifacts are mandatory;
2. how each artifact is digest-linked to the exact revision;
3. which inherited fields must reset on revision registration;
4. retention and immutability requirements; and
5. whether reapproval always requires a new revision or may use an
   authenticated fresh-evidence packet on the rejected revision.

This was the Gate A stop condition. Gate B has since selected and implemented
the new-revision option; this section remains the historical decision input, not
the current behavior statement.

## Required negative tests for an implementation batch

1. Rejecting an explicit historical revision, or recording a blocked security
   scan against it, changes no revision, `skills.status`, scan record, or audit
   event.
2. A queued scan or test superseded before execution fails
   `STALE_TARGET_REVISION`; retry does not retarget.
3. Omitted revision identifiers still resolve to the current revision.
4. Runtime create and resume remain denied after rejection, blocking,
   supersession, or digest drift.
5. If Gate B authorizes fresh reapproval, a rejected revision cannot be
   directly approved and a new revision receives no inherited
   freshness-sensitive evidence.

## Rollout and rollback

Implement A1 as one independently reviewed commit with focused tests followed
by the complete Python/API regression. It requires no schema or data migration.
Rollback is the inverse code commit; existing Governance and Runtime history is
left untouched. Do not combine A1 with fresh reapproval, expiry, revocation,
quorum, cryptographic audit work, FTS5, a new Asset type, or Dashboard redesign.

Any unresolved Critical or Warning finding, stale-job ambiguity, partial-write
test failure, or Runtime regression is a stop condition.
