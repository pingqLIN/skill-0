# Runtime Architecture v1 Baseline

- Status: **Accepted stable foundation**
- Version: `1.0.0`
- Effective date: `2026-07-18`
- Machine-readable baseline: [`contracts/runtime-architecture-v1.json`](contracts/runtime-architecture-v1.json)
- Traditional Chinese companion: [`runtime-architecture-v1.zh-tw.md`](runtime-architecture-v1.zh-tw.md)

## 1. Purpose

This document freezes the supported Runtime Asset architecture after the P0 and
P1 evidence cycles. It turns the implemented compatibility foundation into a
versioned baseline; it does not authorize another feature-development cycle.

The baseline is additive to the accepted Runtime v4 boundary. Runtime Asset is
the identity and revision envelope around the existing Skill payload. Action,
Rule, and Directive remain the decomposition ontology, and Evidence remains an
orthogonal projection over immutable facts.

## 2. Stable boundary

```text
Skill source corpus
  -> SkillParserAdapter
  -> immutable Runtime Asset snapshot (Skill only)
  -> read-only Asset and legacy Skill compatibility APIs
  -> derived search Index

exact Asset revision + canonical payload digest
  -> Governance current-revision approval
  -> Runtime contract and deterministic policy gates
  -> dry-run-only executor
  -> append-only Runtime event ledger
  -> Evidence projection
```

The architecture has five logical planes:

| Plane | Responsibility | Authority |
|---|---|---|
| Asset | Canonical Skill-backed identity, revision, provenance, and immutable process snapshot | Canonical parsed payload and deterministic envelope mapping |
| Index | Rebuildable search projection and bounded query execution | None; an Index result never authorizes a run |
| Governance | Asset-to-governance binding, current revision, approval provenance, and admission decision | Current approved `skill_revisions` row plus exact artifact digest |
| Runtime | Planning, policy evaluation, effect sequencing, HITL, recovery, and reconciliation | Append-only Runtime events; run status is a projection |
| Evidence | Deterministic per-run and aggregate projections | Source event watermark and immutable source facts |

The Knowledge Plane and Agent Evaluation surface are extension points. They may
consume the stable identities and evidence references defined here, but they do
not become authority sources and cannot mutate this baseline implicitly.

## 3. Identity and authority rules

1. `asset_type=skill` is the only supported Runtime Asset type in v1.
2. An Asset revision is content-addressed and maps deterministically to one
   canonical Skill payload. Ambiguous identities fail closed.
3. Governance approval is revision-specific. Mutable Skill status, search rank,
   benchmark score, similarity, or evaluator output cannot grant admission.
4. Runtime admission binds the canonical Asset identity, payload digest,
   governance revision, runtime contract, input, and preflight basis.
5. Runtime events are append-only. `runtime_runs.status`, HITL queue state, and
   Evidence documents are query projections rather than independent truth.
6. External writes require durable identity, an idempotency key, a logical lock
   key, declared risk, and a recovery or reconciliation path.
7. Unknown policy, risk, effect outcome, authority, or snapshot freshness fails
   closed.

## 4. Storage boundary

Version 1 preserves the existing physical topology:

| Store | Logical role | Mutation rule |
|---|---|---|
| `skills.db` | Derived Asset search Index | Rebuildable through explicit, guarded Index maintenance |
| `governance.db` | Governance binding and revision authority | Governance workflow only |
| `runtime.db` | Append-only Runtime ledger and Runtime projections | Runtime ledger transactions only |

No physical database rename, split, merge, authority-row copy, or Runtime history
rewrite is part of this baseline. A future topology change requires a separate
migration proposal, backup and restore rehearsal, rollback proof, and explicit
operator approval.

## 5. Execution boundary

- Architecture v1 is dry-run-only. It contains no available or authorized real
  adapter execution path.
- Existing adapter certification and production-approval structures are dormant
  infrastructure, not execution authority. Activating non-dry-run execution
  requires a separately approved architecture baseline, security gate, and
  release decision; an approval artifact alone is insufficient.
- Framework integrations remain behind adapters. MCP, agent framework, and graph
  checkpoints do not replace the Runtime ledger.
- An ambiguous adapter outcome enters reconciliation. It is never blindly
  retried, compensated, or reported as success.
- Recovery is strict LIFO and succeeds only when a terminal ledger event proves
  the recovery outcome.

## 6. Compatibility guarantees

Within v1:

- existing canonical Skill documents remain valid and byte-unmodified;
- ARD identifiers and semantics remain unchanged;
- legacy Skill API surfaces remain compatibility projections;
- Runtime contracts remain additive and optional for non-runtime Skill use;
- the Asset Index remains derived and replaceable;
- no consumer may require a Dashboard redesign to use the Core Runtime.

An incompatible identity, authority, ledger, or evidence change requires a new
major architecture baseline. Additive extension contracts may increment their
own version without changing Architecture v1 when all rules above remain true.

## 7. Explicit exclusions

The following are not authorized by this baseline:

- FTS5 integration or hybrid search promotion;
- a new Runtime Asset type;
- Dashboard redesign;
- physical database migration;
- any non-dry-run execution;
- search, Knowledge Plane, or benchmark output as Runtime authority;
- treating Evidence as a fourth ARD category.

## 8. Change control and verification

Any change claiming compatibility with Runtime Architecture v1 must:

1. identify the affected plane and authority source;
2. preserve the machine-readable invariants in
   `docs/contracts/runtime-architecture-v1.json`;
3. add focused tests for changed behavior;
4. pass the repository regression baseline (459 tests at adoption); and
5. receive an independent review before commit.

If a proposed change cannot satisfy an invariant, it must be handled as a new
architecture version rather than silently weakening v1.
