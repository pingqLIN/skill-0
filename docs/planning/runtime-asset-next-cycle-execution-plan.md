# Runtime Asset Next-Cycle Execution Plan

**Status:** Approved execution scope; operator decisions remain explicit gates

**Date:** 2026-07-18

**Authority:** English version; see the Traditional Chinese companion for reference

## Goal

Complete the next Runtime Asset cycle in four ordered stages without weakening the
P0 compatibility boundary:

1. establish a real, auditable Governance authority for the 196 current Assets;
2. prove strict drift-doctor health and reversible restore behavior;
3. review dependency and supply-chain security with reproducible evidence; and
4. expand the P1 Search experiment to a frozen, independently reviewed evidence set.

Production FTS5, a second Asset Type, physical database consolidation, and Dashboard
renaming remain outside this cycle unless a later P1 decision explicitly authorizes
them.

## Execution mode and gates

- Scale: **Large**. Execution is phased and non-interactive where actions are local,
  reversible, and already within the approved scope.
- Each stage receives an implementation review and focused tests before its commit.
- Generated review packets, decision manifests, databases, backups, and benchmark
  evidence stay in ignored local paths.
- An AI agent may prepare and validate an operator decision packet, but it must not
  invent a human reviewer, approval reason, or approval decision.
- Database publication, dependency mutation, and any public push remain explicit
  gates. A failed gate stops only the affected stage and is reported truthfully.

## Pre-stage — production security hardening closure

**Status:** Local source and contract hardening and the isolated Compose
technical rehearsal completed on `2026-07-20`; production clearance remains
blocked by the separate security and external-control gates.

### Delivered local controls

- Production startup and `runtime_doctor --production` reject
  `SKILL0_RUNTIME_ALLOW_INITIALIZE=true`; production boots cannot initialize an
  empty Runtime ledger.
- Public `/health` returns a liveness status only. Authenticated
  `/api/health/detail` omits filesystem, storage, model, and version metadata.
- The isolated Compose rehearsal initializes its disposable Runtime volume before
  production startup through an entrypoint-overridden helper, then runs the
  stack with Runtime initialization disabled throughout.
- [`../production-security-policy.md`](../production-security-policy.md) is
  advanced to policy `1.2.0`; the two controls are no longer listed as known
  unenforced gaps.

### Validation evidence

- Focused production contract regression: `6 passed`.
- Full Python/API regression: `503 passed, 76 warnings`.
- Schema validation: `196 passed, 0 failed`.
- The isolated PowerShell Compose rehearsal passed service health, production
  doctor, governed dry-run, deterministic Evidence, three-store backup/restore,
  restart persistence, and cleanup checks. See
  [`../reports/runtime-production-compose-rehearsal-2026-07-20.md`](../reports/runtime-production-compose-rehearsal-2026-07-20.md).
- The local Git worktree was clean before this batch; no Asset type, FTS5
  integration, Dashboard redesign, real adapter, or physical database migration
  was introduced.

### Rehearsal evidence and remaining production boundary

The requested live isolated rehearsal is now `TECHNICAL_REHEARSAL_PASS`. It used
synthetic rehearsal-only values, loopback ports, a unique Compose project, and
disposable volumes; it did not read real production configuration or create a
public route. The first run exposed repository-local Governance DB copy-up into
the Dashboard image. Commit `0b3acbb` removed that image input and added a build
context guard; the clean rerun passed and left zero project containers, volumes,
or networks.

This does not grant production clearance. The dependency/image review remains
`PRODUCTION_NO_GO_PENDING_BASE_CVE_FIX`, Dashboard/Web image vulnerability state
remains `UNKNOWN`, and external TLS, network, secret-manager, encrypted-backup,
and monitoring controls still require operator evidence.

## Stage 1 — P0.2 real Governance authority

### Deliverables

- Add `tools/runtime_asset_governance_bootstrap.py` with separate `preview`,
  `validate-decision`, and `apply` commands.
- `preview` builds an immutable 196-item packet from
  `LegacySkillAssetRepository`, including the corpus snapshot, canonical Asset ID,
  revision ID, content digest, source path/digest, identity strategy, version, and
  read-only security-scan summary.
- The packet has a deterministic digest over canonical JSON. Volatile creation time
  is excluded from the digest.
- An operator decision manifest is bound to the packet digest and snapshot. Every
  candidate must be explicitly approved or rejected with a reviewer identity and
  non-empty reason.
- `apply` rebuilds and validates the packet before any mutation, creates a private
  staging Governance database, uses the existing `GovernanceDB` lifecycle, verifies
  database integrity and audit provenance, and publishes atomically only when all
  required checks pass.

### Safety rules

- Never reuse the unrelated root `governance.db`.
- Never write a partial authority database to `governance/db/governance.db`.
- The P0.2 bootstrap refuses an existing target. Backup, restore, and replacement are
  separate Stage 2 operator workflows; the bootstrap never mutates live authority
  state in place.
- A rejected or omitted Asset cannot produce a false `healthy` doctor state.
- Canonical Asset ID is the unique Governance record name. Human display names stay
  in evidence only, avoiding the existing duplicate `pdf` names.

### Acceptance

- Packet determinism and all fail-closed decision validation tests pass.
- The three source-name-derived Java canonical IDs bind without ambiguity.
- A fully approved test corpus produces doctor `healthy` / exit `0` using the real
  Governance schema; a rejection produces `authority-missing` / exit `2`.
- A real operator decision is available for the live 196-item apply. Until then,
  Stage 1 is `AWAITING_OPERATOR_DECISION`, not complete.

## Stage 2 — strict doctor health and restore

### Execution

1. Apply the exact reviewed decision to a staging database.
2. Verify `PRAGMA integrity_check`, 196 current canonical bindings, exact content
   digests, approval provenance, and expected audit-event counts.
3. Publish the staged database atomically.
4. Run Runtime Asset index maintenance without
   `--allow-nonhealthy-evidence`, then run a second no-op maintenance pass.
5. Run the standalone doctor and Runtime admission probes for one ordinary Asset and
   one derived Java canonical Asset.
6. Rehearse restore from the verified backup/copy and re-run the doctor.

### Acceptance

- Strict maintenance is accepted without an exception flag.
- The second pass is a no-op.
- Doctor is `healthy` / exit `0` before and after the restore rehearsal.
- The source Registry snapshot and derived Index identity remain unchanged.

## Stage 3 — security and dependency review

### Evidence batches

- Run npm lockfile audits for development and production scopes under the Node 20
  project target.
- Resolve Python dependency graphs in disposable, ignored environments and audit
  them without changing the repository environment.
- Review container base-image pinning, Python lock coverage, GitHub Actions pinning,
  and CI advisory gates separately.
- Read GitHub Dependabot alerts only when authenticated read-only access is available;
  otherwise record their state as `UNKNOWN`.

### Remediation rules

- Critical/high runtime-direct findings block release or push until fixed or covered
  by an evidence-based, expiring exception.
- Apply the smallest ecosystem-scoped change; never perform broad upgrades or
  unrelated lockfile churn.
- Dependency edits are a separate mutation batch with focused tests, full regression,
  and their own commit.

### Acceptance

- No untreated critical/high finding in the inspected runtime graphs and images.
- Every deferral records package/advisory, reachability, owner, expiry, and a
  revalidation command.
- Node 20 lint/test/build, Python regression, relevant Docker builds, and a scoped
  secret/artifact review pass after any remediation.

## Stage 4 — expand P1 Search evidence

### Frozen protocol

- Add a new, non-overwriting v2 suite with 84 queries: 42 lexical and 42 semantic,
  at least 40 distinct direct targets, and 1–3 graded qrels per query.
- A curator works only from corpus metadata/payload. A second reviewer adjudicates
  wording, target resolution, subset labels, and taxonomy coverage before any
  retrieval measurement.
- Freeze the suite digest, corpus snapshot, qrel count, and taxonomy matrix before
  running the benchmark.
- Pre-register three FTS5 profiles: current baseline, `detail=none`, and
  `detail=none,columnsize=0`. Mapping-table bytes count toward storage.
- Do not reduce indexed content, change tokenization/weights, or edit qrels after
  seeing results to satisfy the 25% storage gate.

### Acceptance

- All existing quality, recall, latency, isolation, 196-projection, query coverage,
  and storage gates are evaluated for every registered profile.
- Select the smallest profile only among profiles that pass every other gate.
- Publish an English authoritative decision report and `.zh-tw.md` companion that
  includes all profiles.
- `GO_P1_PROTOTYPE` authorizes only a later reviewed prototype plan. Any failed gate
  produces an evidence-backed `NO_GO` and keeps production vector-only.

## Final integration and rollback

- Run schema validation, Python regression, frontend checks, and documentation/link
  checks appropriate to all changed surfaces.
- Review staged diffs and generated evidence for secrets and accidental planning-data
  publication before any future push.
- Each completed batch is committed independently. No push, release, database
  consolidation, or production FTS5 activation is authorized by this plan.
- Source changes roll back through their individual commits. Local authority state
  rolls back through the verified SQLite backup; failed staging artifacts are simply
  discarded without touching the live target.
