# Governance Authority Lifecycle v1

- Status: **Accepted stable-foundation authority model**
- Version: `1.1.0`
- Effective date: `2026-07-20`
- Machine-readable lifecycle: [`contracts/governance-authority-lifecycle-v1.json`](contracts/governance-authority-lifecycle-v1.json)
- Runtime admission: [`runtime-governance.md`](runtime-governance.md)
- Traditional Chinese companion: [`governance-authority-lifecycle.zh-tw.md`](governance-authority-lifecycle.zh-tw.md)

## 1. Purpose

This document defines when a Governance revision has Runtime admission authority,
how that authority begins and ends, and which records remain evidence rather than
authority. It documents the current implementation as a stable foundation; it
does not create a new database lifecycle or authorize a physical migration.

## 2. Evidence state

### VERIFIED implementation

- `skills.skill_id` is the Governance identity; `skills.canonical_skill_id` is
  the unique binding to a canonical Skill Asset identity.
- `skills.current_revision_id` selects one current `skill_revisions` row.
- A new revision becomes current with `status=pending` and clears its Runtime
  artifact binding and approval provenance.
- Runtime artifact binding is permitted only for the pending current revision
  and records the exact canonical artifact digest.
- Approval requires a canonical identity and artifact digest, and updates the
  current revision with `status=approved`, `approved_by`, and `approved_at`.
- Runtime admission reads the current revision and exact digest; it ignores the
  mutable `skills.status` projection as an authority source.
- Create and resume both re-evaluate Governance. Supersession, current-revision
  rejection or blocking, missing provenance, or artifact drift denies admission.
- `approve_skill()` can currently return a rejected current revision with a
  retained binding directly to `approved`; it does not require a new binding or
  fresh decision-evidence field.
- Approve, reject, security-scan, and equivalence-test writes resolve the exact
  current revision in their write transaction. Explicit stale targets fail
  before revision, projection, evidence, or audit writes.
- Dashboard scan/test jobs preserve their captured `target_revision_id` through
  execution. Superseded jobs fail as `STALE_TARGET_REVISION` and are not
  retriable; an operator must enqueue a new job for the current revision.
- Governance decisions are appended to `audit_log`; Runtime decisions and
  execution history remain in the separate Runtime ledger.

### INFERRED stable interpretation

- An approval is authority for one exact tuple, not for a mutable Skill name or
  all future revisions.
- Registering a new revision supersedes the old revision's authority even though
  its historical approval fields remain for audit.
- Rejection or blocking of the current revision ends admission authority; it
  does not delete the revision or rewrite prior Runtime evidence.
- Canonical payload drift creates a derived `drifted` condition. The stored row
  need not change state for Runtime admission to fail closed.

### UNKNOWN / current gaps

- Governance approvals have no implemented expiry or renewal clock.
- There is no dedicated append-only `revoked` decision type. Current authority
  is ended by rejection, blocking, supersession, or failed exact admission.
- Actor separation-of-duties and quorum are deployment policy, not enforced by
  the current schema.
- Re-approval after rejection does not enforce rebinding or fresh evidence.
- `skills.status` and revision status are mutable projections. `audit_log`
  records decisions but is not cryptographically chained.

These remaining gaps must not be described as implemented controls. Production
policy may fail closed around them. Any future persistence change still needs a
separately approved design and migration.

## 3. Authority unit

Runtime authority is the exact conjunction:

```text
governance_skill_id
+ current revision_id and is_current=1
+ revision status=approved
+ canonical Asset identity binding
+ exact canonical artifact_digest
+ matching Skill version
+ non-empty approved_by and valid approved_at
```

If any element is absent, stale, ambiguous, or mismatched, the revision is not
authoritative. Search results, Asset Index rows, `skills.status`, Dashboard state,
Knowledge Plane context, benchmark reports, Runtime contracts, and prior run
success cannot substitute for this tuple.

## 4. Lifecycle states

| State | Meaning | Runtime authority |
|---|---|---|
| `pending-unbound` | Current revision exists but lacks exact canonical identity and/or digest binding | No |
| `pending-bound` | Current revision is bound to the exact Asset identity and digest and awaits decision | No |
| `approved-current` | Exact bound current revision has approval actor and timestamp | **Yes, subject to create/resume revalidation** |
| `rejected-current` | Current revision has an explicit rejection decision | No |
| `blocked-current` | Current revision status is blocked by a Governance workflow | No |
| `superseded` | Historical revision is no longer current | No |
| `drifted` | Stored approval no longer matches canonical Asset content, version, identity, or currentness | No |

Only `approved-current` is admission-authoritative. Approval of a non-current
revision is invalid, and historical approval fields are evidence only.

## 5. Transitions and gates

### Register

Creating a Governance Skill creates revision 1 as `pending-unbound`. Registering
a later revision atomically makes it current, marks prior revisions non-current,
and resets the new revision to pending/unbound. Approval never carries forward.

### Bind

Binding is a server-side operation over the pending current revision. The server
loads the canonical Skill payload, resolves the canonical Asset identity,
computes the digest, and records the authenticated actor. Request input cannot
supply a trusted actor or digest. Rebinding an already approved revision is
rejected only when the identity or digest differs. An identical identity and
digest returns idempotent success before the status check, including for an
approved, rejected, or blocked current revision; that return does not change the
revision's authority state.

### Review and decide

Scans, tests, and review packets are decision evidence. They do not themselves
grant authority. Initial approval creates `approved-current` only after exact
binding. The current implementation also permits a bound `rejected-current`
revision to return directly to `approved-current`; it does not prove that fresh
evidence was collected. A blocked current revision cannot be overridden by the
normal approval call.

Rejection creates `rejected-current` only when the targeted revision is current.
Blocking creates `blocked-current` only when a security scan writes against the
current revision. Non-current reject, scan, and equivalence targets fail before
any projection or evidence write. A standalone `skills.status` projection
change is not authority and cannot by itself grant or remove Runtime admission.

### Supersede, revoke effect, and drift

- A new current revision makes the prior revision `superseded` immediately.
- Rejecting or blocking the current revision ends its admission authority.
  Authority-affecting and evidence writes cannot target a historical revision.
- Exact identity, version, digest, currentness, or approval-provenance mismatch
  yields `drifted` at admission time and fails closed.
- Because no dedicated revocation event exists, operators must preserve the
  audit decision and use an implemented state change; documentation must not
  claim an independent revocation mechanism.

### Re-approve

The current approval method can restore a bound rejected current revision
directly; that is implementation behavior, not proof of a fresh review. A
blocked current revision is rejected by the approval method. Current-target
enforcement is implemented, but until a stronger workflow exists production
policy should require fresh decision evidence before re-approval and must not
claim that the database enforces rebinding, expiry, quorum, or evidence
freshness.

## 6. Runtime interaction

1. **Create:** admission reads the exact current approved revision and canonical
   digest. Failure creates no authorized execution basis.
2. **Persist:** an admitted run stores Governance revision identity in its keyed
   execution basis and records the attestation in the append-only ledger.
3. **Resume:** Governance and canonical identity are checked again before the
   one-time resume claim is consumed. Changed authority denies resume.
4. **History:** later rejection, blocking, drift, or supersession does not alter
   already appended events or derived historical Evidence.
5. **HITL:** Runtime approval and recovery decisions are separate Runtime-ledger
   authority. They cannot create Governance approval or repair a stale revision.

## 7. Ownership and actor boundary

| Actor/surface | May do | Must not be treated as |
|---|---|---|
| Parser / Asset repository | Resolve canonical payload, identity, revision, digest | Governance approver |
| Governance service | Bind, scan, test, approve, reject, block, audit | Runtime effect ledger |
| Authenticated reviewer | Supply a decision through an authorized server workflow | Source of client-provided trusted digest/actor |
| Core Runtime gate | Read and attest exact current Governance authority | Mutator of Governance approval |
| Runtime HITL actor | Approve a bounded action or confirm recovery | Governance revision approver |
| Dashboard | Present workflows and submit authenticated requests | Authority database or policy engine |
| Knowledge / Evaluation planes | Supply context or evidence-only measurements | Admission authority |

## 8. Audit and retention

For every authority-affecting decision, retain the Governance Skill ID, revision
ID, canonical Asset ID, artifact digest, actor, timestamp, reason, decision
evidence reference, previous state, and new state. Never delete historical
revisions or rewrite Runtime events to make current state appear continuous.

An incident review must be able to answer:

- which exact revision was current and approved at admission;
- which canonical digest was checked;
- who decided and from which authenticated subject;
- which later transition ended authority; and
- whether a resume was denied after that transition.

## 9. Change control

Changing the authority tuple or current-target semantics, hardening re-approval,
adding approval expiry, adding revocation/quorum, or changing
persistence semantics requires focused tests, independent review, and an
explicit migration plan if storage changes. Runtime Architecture v1 does not
authorize those changes by itself. See
[`governance-authority-lifecycle-proposal.md`](governance-authority-lifecycle-proposal.md)
for the required operator decisions and staged design gates.
