# Governance Authority Gate A Compatibility Design v1

- Status: **Reviewed design; no implementation authority**
- Date: `2026-07-20`
- Decision proposal: [`governance-authority-lifecycle-proposal.md`](governance-authority-lifecycle-proposal.md)
- Current behavior: [`governance-authority-lifecycle.md`](governance-authority-lifecycle.md)
- Traditional Chinese companion: [`governance-authority-gate-a-design.zh-tw.md`](governance-authority-gate-a-design.zh-tw.md)

## Purpose and boundary

This Gate A artifact defines a compatibility-only implementation shape for
current-target enforcement and records the unresolved decisions for fresh
reapproval. It does not authorize code changes, alter the authority tuple,
change Runtime admission, add an Asset type, redesign the Dashboard, or permit
a physical database migration.

The exact current approved Governance revision and matching canonical identity,
artifact digest, version, approver, and approval timestamp remain the only
Runtime authority. Mutable projections, jobs, scans, Search, Knowledge, and
Evaluation remain non-authoritative.

## Verified baseline

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

Use the resolver from `reject_skill()` and the authority-affecting
`record_security_scan()` path. `approve_skill()` keeps its existing currentness
guard but should converge on the same resolver during implementation so all
three operations share one rule.

### Dashboard job boundary

The action worker must pass the immutable job `target_revision_id` through
`run_scan()` into `record_security_scan()`. If a new revision supersedes that
target before execution, the job fails as `STALE_TARGET_REVISION`; it must not
retarget, scan the replacement revision, update projections, or emit successful
scan evidence. Retry remains bound to the original target. An operator must
enqueue a new job for the new current revision.

Existing synchronous callers that omit `revision_id` retain current behavior.
The implementation batch must choose and document one stable mapping for stale
explicit callers—domain exception, false result, or structured service error—
before changing public API behavior. HTTP routes need no new request field for
Gate A unless that mapping cannot be contained in the service layer.

### Candidate files

| File | Intended change |
|---|---|
| `tools/governance_db.py` | Transaction-local current-target resolver; use it for approve, reject, and authority-affecting scan writes. |
| `skill-0-dashboard/apps/api/services/governance.py` | Pass captured target through scan execution; fail stale jobs without retargeting. |
| `skill-0-dashboard/apps/api/routers/skills.py` | Only if required to normalize a stale-target response; no UI redesign. |
| `tests/test_governance_revisions.py` | Negative DB tests for stale reject/scan and zero side effects. |
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

Until those decisions exist, direct reapproval remains a documented gap and no
implementation may claim to enforce fresh evidence.

## Required negative tests for an implementation batch

1. Rejecting an explicit historical revision, or recording a blocked security
   scan against it, changes no revision, `skills.status`, scan record, or audit
   event.
2. A queued scan superseded before execution fails
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
