# Runtime Asset P0 Verification and P1 Decision Packet

- Status: **P0 implementation verified; operator migration not executed**
- Date: `2026-07-17`
- Scope authority: [`../planning/runtime-asset-foundation-next-round-plan.md`](../planning/runtime-asset-foundation-next-round-plan.md)
- Traditional Chinese companion: [`runtime-asset-p0-verification-and-p1-decision.zh-tw.md`](runtime-asset-p0-verification-and-p1-decision.zh-tw.md)

## Outcome

P0 Runtime Asset Foundation and Storage Boundary is complete at the code,
contract, fixture, API, and doctor layers. Existing Skill and Runtime v4
contracts remain available. No physical database was renamed, split, merged, or
migrated; no operator `skills.db`, Governance DB, or Runtime DB was changed.

## Commit series

| Batch | Commit | Result |
|---|---|---|
| P0-A contracts | `f840a09` | Envelope v1, ADR-0007/0008, failure fixtures, compatibility map |
| P0-B repository | `e09fc47` | immutable corpus snapshot, Skill adapter, Runtime lookup binding |
| P0-C storage | `b9724a3` | SQLite policy, checksum migration, backup/restore fixtures |
| P0-D search/index | `813d097` | bounded async offload, projections, incremental identity |
| P0-E API/doctor | `b07b194` | read-only Asset API and classified drift doctor |

## Integrated verification

| Gate | Result |
|---|---|
| Python compileall | Passed |
| Document status markers | Passed |
| Shared-document contract | Passed |
| Parsed schema | `196 passed, 0 failed` |
| Full Python regression | `414 passed, 66 warnings` |
| P0-E pre-cut full regressions | `403 passed` twice consecutively |
| Frontend lint | Passed |
| Frontend tests | `34 passed` |
| Frontend build and bundle guard | Passed; largest JS chunk `336.35 KiB` under `350 KiB` |
| Diff whitespace check | Passed |

The warnings are the existing test warning class; no failure was suppressed.

Two independent read-only completion reviews passed after their initial
findings were fixed and re-reviewed. The closed findings covered atomic
authenticated reload, production connection-factory usage, migration checksum
doctor visibility, model-weight identity, and shared-operation concurrency.

## Storage and migration evidence

- Fresh/current/legacy fixture databases converge through ordered migrations.
- Migration records bind immutable SHA-256 checksums and runner version.
- An edited migration checksum fails closed.
- A competing writer returns classified `sqlite_write_contention`.
- Read-only preview creates no table or database artifact.
- SQLite backup uses the backup API and passes `integrity_check` plus a restored
  read.
- No operator migration was run. The L3 preview/backup/approval gate remains
  mandatory before applying `schema_migrations` and `asset_index_state` to a
  real `skills.db`.
- Production API Index operations use factory-backed per-unit-of-work
  connections. The doctor exposes ordered migration status and classifies an
  applied-checksum mismatch as `unknown`/exit `3` rather than continuing.

## Incremental index and async evidence

- First two-item fixture run: two changed representations.
- Second unchanged run: zero embeddings, two unchanged.
- One parser-version drift: one changed and one unchanged.
- Representation-version drift: both representations selected.
- Local embedding-model identity includes every model file, including weight
  artifacts; remote/non-local models require an explicit immutable
  `SKILL0_EMBEDDING_MODEL_VERSION`. Weight drift selects affected revisions.
- Removed source: one stale projection pruned.
- Injected embedding failure: prior index-state rows remained unchanged.
- Search/list hot-path SQL no longer selects `raw_json`.
- Async capacity is fixed at two workers plus four queued calls. The test keeps
  lightweight event-loop work below the 250 ms threshold in at least 9/10 runs;
  the next saturated request fails within 250 ms and cancellation does not
  prematurely release a still-running thread slot.

## Runtime lookup and compatibility evidence

- Runtime create/resume resolves through one immutable process-local repository.
- Request paths do not re-enumerate or reparse the corpus.
- Known-file metadata drift or directory-entry drift returns
  `stale_source_snapshot` before Runtime execution.
- Authenticated `POST /api/assets/reload` validates a replacement snapshot off
  to the side and swaps the process reference only after success; the
  stale-to-reloaded recovery fixture passes.
- All 196 documents remain byte-unmodified and schema-valid.
- The three `claude__skill__java_to_java_upgrade` documents remain an explicit
  ambiguous identity: list/revision inspection works and single-detail/Runtime
  lookup fails closed.
- Legacy numeric `/api/skills/{id}`, pagination, `include_json`, search, and
  index compatibility tests remain green. New Asset endpoints are additive and
  read-only; payload is excluded unless detail explicitly requests it.

## Current doctor evidence

The local doctor result is `authority-missing` with exit code `2`:

- Registry revisions: `196`;
- migrated Asset index rows: `0`;
- pending projections: `196`;
- duplicate canonical identities: `1`;
- Governance operator database: missing.

This is the correct observed local state. It must not be changed by an implicit
migration or synthetic governance authority. The doctor schema and tests also
prove `healthy`, `stale-derived-projection`, and `unknown` classifications.

## P1 decisions

| Candidate | Decision | Evidence gate required to reopen |
|---|---|---|
| Physical DB reorganization | **NO-GO** | operator-copy migration rehearsal, restore timing, contention, size, and operating-cost measurements |
| FTS5/hybrid ranking | **NO-GO — pilot evidence insufficient** | 18-query pilot passed directional quality/latency but failed the 80-query coverage and 25% storage gates; see [`runtime-asset-p1-search-evidence.md`](runtime-asset-p1-search-evidence.md) |
| Second Asset Type | **NO-GO** | accepted ground-truth corpus, parser contract, failure taxonomy, and measured fidelity |
| Dashboard Asset rename | **NO-GO** | stable second type or measured operator need, versioned API usage evidence, and migration/rollback design |

P1 may be proposed from new evidence, but none of these candidates is implied by
P0 completion.

## Rollback and residual risk

Each batch is an independent additive commit and can be reverted in reverse
order. No operator data rollback is needed because no operator DDL ran. If the
Index migration is later approved and must be reversed, restore its verified
pre-migration backup; do not drop tables in place.

Residual risk is limited to the intentionally unexecuted operator migration and
the current ambiguous Java canonical identity. Incremental Asset search remains
unavailable on an unmigrated Index, while legacy Skill search remains the
compatibility path.
