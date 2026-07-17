# Runtime Asset Foundation — Next-Round Development Plan

- Status: **P0 implementation complete; Runtime v4 release authority remains frozen**
- Date: `2026-07-17`
- Target baseline: `main` at P0 plan commit `24c6f0f`
- Planned milestone: `P0 Runtime Asset Foundation and Storage Boundary`
- Traditional Chinese companion: [`runtime-asset-foundation-next-round-plan.zh-tw.md`](runtime-asset-foundation-next-round-plan.zh-tw.md)

## 1. Decision

The next development round should establish an additive, compatibility-first Runtime Asset foundation. It should not immediately rename physical databases, rewrite the parser, expose real adapters, or redesign the Dashboard.

The target architecture is:

```text
Source
  -> Parser Adapter
  -> Runtime Asset Envelope
  -> Revision-aware Registry Boundary
  -> Derived Search Projection
  -> Governed Runtime Admission
  -> Append-only Runtime Ledger
```

`Skill` remains a supported `asset_type` and the only production-supported type during P0. Existing Skill contracts remain operational through explicit compatibility adapters.

This plan opens a proposed post-closeout milestone. It does not silently alter the frozen Runtime v4 release boundary documented in [`../README.md`](../README.md) and [`../closeout/FINAL_REPORT.md`](../closeout/FINAL_REPORT.md).

## 2. Inputs and evidence state

### User-provided proposal inputs

- `skill-0-runtime-asset-item-replacement-checklist.md`
- `skill-0-runtime-asset-integrated-database-recommendations.md`

These documents are design inputs, not repository authority. Their recommendations were checked against the current code and closeout documents before inclusion here.

### VERIFIED current-state findings

1. Runtime run creation and resume still locate canonical Skill JSON by scanning `parsed/*.json` in `api/routers/runs_v4.py`.
2. Core API search endpoints are `async`, but call synchronous model initialization, embedding, SQLite, and vector-search code directly in `api/main.py`.
3. The administrative index endpoint clears the store and performs a full directory re-index. The index has no revision/content/model identity gate.
4. `vector_db/vector_store.py` remains Skill-specific and reads `raw_json` in search/list SQL even where the HTTP response later projects it away.
5. Governance schema evolution is implemented through inline DDL and `_ensure_column`; Runtime schema exists both in `migrations/001_runtime_ledger.sql` and `RuntimeLedger._migrate()`.
6. Governance revision status and artifact digest—not mutable Skill status—are the Runtime admission authority. This boundary must remain intact.
7. Runtime v4 is a dry-run-only, single-host pilot with an append-only Runtime ledger. Real adapter loading and non-dry-run API behavior remain separately gated.
8. The consolidated baseline passes 374 Python tests, 34 frontend tests, frontend lint, and `build:ci` on Windows after enforcing LF for digest-bound certification artifacts.

Reproducible evidence anchors at baseline `7257ea1`:

- [`../closeout/VERIFICATION_MATRIX.md`](../closeout/VERIFICATION_MATRIX.md) records the closeout command matrix.
- `api/routers/runs_v4.py` contains the request-time canonical JSON scan.
- `api/main.py`, `vector_db/search.py`, and `vector_db/vector_store.py` contain the synchronous search, full index, and payload-selection paths.
- `tools/governance_db.py`, `runtime/ledger.py`, and `migrations/001_runtime_ledger.sql` contain the current schema-evolution paths.
- This plan was prepared after a fresh Windows run of the full Python command (`374 passed`), frontend lint, frontend tests (`34 passed`), and `build:ci`; those results support planning but do not replace the immutable closeout evidence.

### INFERRED design conclusions

1. A Runtime Asset envelope can generalize identity and revision metadata without changing ARD decomposition semantics.
2. Repository interfaces can contain legacy Skill storage while allowing later Registry/Index separation.
3. A one-time legacy artifact catalog can remove request-time directory scans before a physical Registry migration.
4. Index identity based on revision, content, representation, and model versions can support safe incremental indexing.

These are architectural hypotheses until implemented and tested.

### UNKNOWN and deliberately deferred

- Whether the eventual physical topology should be `registry.db + index.db + runtime.db` or `assets.db + runtime.db`.
- Whether FTS5 materially improves the project workload and which score-fusion method is appropriate.
- Which Registry/Index PRAGMA and durability settings perform best under a defined workload.
- Parser accuracy by asset type; no accepted ground-truth benchmark currently supports parser expansion.
- Whether Workflow should be the second asset type; it is a candidate, not a P0 commitment.
- Migration cost and rollback behavior for real operator databases.

## 3. Goals

P0 must:

1. Ratify `Runtime Asset`, `asset_id`, `asset_type`, and `revision_id` as additive generic-domain terminology.
2. Define Runtime Asset Envelope v1 with a Skill compatibility mapping and failure fixtures.
3. Wrap existing Skill parsing behind a `SkillParserAdapter` without rewriting parser behavior.
4. Introduce narrow SQLite repository, connection, and migration boundaries without multi-engine abstraction.
5. Remove repeated `parsed/*.json` scans from Runtime request paths.
6. Offload synchronous search/model work from the API event loop with bounded execution.
7. Make search projection explicit and stop selecting `raw_json` on search/list hot paths.
8. Add index identity sufficient to skip unchanged embeddings.
9. Make Registry/Index drift observable through the existing doctor/reporting family.
10. Preserve every Runtime v4 governance, evidence, HITL, recovery, and dry-run invariant.

## 4. Non-goals

P0 will not:

- rename or merge `skills.db`, `governance.db`, or `runtime.db`;
- create `runtime_assets`/`asset_revisions` as a production migration;
- move or rename `parsed/`;
- delete or deprecate `/api/skills` or existing search routes;
- rename Dashboard components or redesign the review experience;
- add FTS5 ranking to the production path before a benchmark and scoring decision;
- add Workflow, Prompt, Agent, Tool, MCP, API, Model, Dataset, or Policy parsing;
- modify ARD IDs or treat Evidence as a fourth ARD peer;
- enable a real action adapter or `dry_run=false`;
- introduce PostgreSQL, D1, LMDB, DuckDB, a graph database, or a generic storage-engine plugin layer;
- expand into multi-instance, HA, multi-tenant, or Edge deployment.

## 5. Non-negotiable architecture invariants

1. **ARD remains the decomposition ontology.** Runtime Asset is a catalog/revision envelope, not a replacement for Actions, Rules, and Directives.
2. **Governance remains revision-authoritative.** Runtime admission must continue to bind the exact canonical artifact digest to the approved current governance revision.
3. **The search index is derived.** It must be rebuildable and must never authorize execution.
4. **The Runtime ledger remains separate and append-only.** No asset migration may rewrite Runtime history.
5. **Legacy compatibility is explicit.** Skill APIs and schemas route through adapters; historical migrations, events, fixtures, and audit values are not globally renamed.
6. **New generic code uses Asset terminology.** Skill terminology remains only in Skill adapters and compatibility surfaces.
7. **Failure is closed and observable.** Stale Registry/Index identity, ambiguous canonical identity, migration checksum drift, or missing governance binding must fail with a classified result.

## 6. Required pre-implementation decisions

Batch P0-A must produce and approve these proposal documents before any later batch may mutate storage:

1. **ADR-0007 — Runtime Asset terminology and compatibility**
   - identity rules;
   - Skill-to-Asset mapping;
   - legacy API and event-name retention;
   - authority of English docs and schemas.
2. **ADR-0008 — Registry, Index, and Runtime storage boundary**
   - logical authority;
   - derived-projection semantics;
   - transaction/outbox direction;
   - explicit deferral of physical database topology.
3. **Compatibility map**
   - classify each `skill_*` occurrence as domain-generic, Skill adapter-specific, legacy compatibility, historical/migration, fixture, or documentation-only;
   - prohibit global search-and-replace.

No physical table rename or data copy is authorized by these ADRs.

## 7. Execution batches

### P0-A — Contracts, failure cases, and compatibility map

Deliverables:

- ADR-0007 and ADR-0008, each with `.zh-tw.md` companion;
- `schema/runtime-asset-envelope.schema.json`;
- valid Skill-backed envelope fixture;
- invalid fixtures for missing revision identity, unsupported type, digest mismatch, and malformed provenance;
- machine-readable legacy compatibility map;
- schema/document contract tests.

Envelope minimum fields:

```text
schema_version
asset_id
revision_id
asset_type
name
summary
payload
content_hash
source_digest
parser_id
parser_version
provenance
lifecycle
```

Acceptance:

- no change to existing Skill schema or Runtime contract behavior;
- all new invalid fixtures fail for the intended reason;
- a canonical Skill maps deterministically to one Asset envelope and back to the existing Skill payload;
- the new schema has an explicit migration/compatibility statement, satisfying deferred-backlog gate D-07.

Rollback: remove the additive schema, fixtures, and ADRs. No data migration exists.

### P0-B — Parser adapter and repository boundary

Deliverables:

- small `asset_registry` package containing the domain model and repository protocols;
- `SkillParserAdapter` wrapping current parser output without changing extraction logic;
- `LegacySkillAssetRepository` that builds an immutable identity map once per configured corpus snapshot;
- duplicate-ID, malformed-document, and digest-drift diagnostics;
- dependency injection for Runtime canonical lookup.

Runtime transition:

```text
load_canonical_skill() directory scan
  -> AssetRepository.get_revision(asset_id, revision_id?)
  -> legacy Skill adapter during P0
```

Snapshot lifecycle:

- `snapshot_id` is the SHA-256 of sorted relative paths plus each canonical file digest and parser identity;
- build and validate a replacement map off to the side, reject duplicates/malformed documents, then atomically swap the process-local reference;
- rebuild only at process startup or an authenticated explicit reload/index action; file changes are never silently admitted mid-request;
- the doctor compares the live corpus snapshot with the active map and reports `stale_source_snapshot` until a successful rebuild;
- each worker owns one immutable snapshot in P0. Cross-worker snapshot coordination is deferred until multi-worker operation is approved.

Acceptance:

- Runtime create/resume paths perform no request-time directory enumeration after repository initialization;
- duplicate canonical identities still return a conflict rather than choosing one;
- governance artifact digest checks remain byte-for-byte identical;
- all 196 checked-in documents remain byte-unmodified and schema-valid, and their existing normalized ARD payload hashes remain unchanged.

Rollback: restore the current loader through one dependency binding; parsed files remain untouched.

### P0-C — SQLite connection and migration foundation

Deliverables:

- one SQLite connection factory with named Registry, Index, and Runtime policies;
- per-unit-of-work connections for new Registry/Index code;
- explicit `foreign_keys`, `busy_timeout`, transaction mode, and durability configuration;
- checksum-aware migration runner with `schema_migrations` contract;
- read-only migration status/doctor output;
- baseline adapters for existing inline schemas.

Allowed P0 DDL inventory:

| Store | Allowed additive DDL | Trigger |
|---|---|---|
| `skills.db` | `schema_migrations` and `asset_index_state` only | Explicit authenticated index maintenance after migration preview and backup |
| `governance.db` | None on operator databases; schema equivalence is exercised on fixture copies only | P1 decision |
| `runtime.db` | None; existing Runtime migration behavior remains authoritative | Separate Runtime migration project |

In this plan, **physical topology/data migration** means renaming database files, merging/splitting stores, copying authority rows between stores, or rewriting Runtime history. It is prohibited in P0. **Additive schema migration** means only the two approved Index tables above; it is permitted behind the explicit migration gate and is not a topology decision.

Constraints:

- do not change Runtime durability defaults;
- do not silently enable WAL or `synchronous=NORMAL` across all stores;
- do not delete inline migration code until an equivalence fixture proves the SQL runner produces the same schema, indexes, and triggers;
- do not migrate operator databases automatically on API import.
- before the one allowed Index migration, record the exact target, run a read-only preview, create and verify a recoverable backup, and obtain the normal L3 runtime-mutation checkpoint.

Acceptance:

- fresh, current, and legacy fixture databases converge to the expected schema;
- edited migration checksum fails closed;
- two writers produce a bounded, classified contention result under the test policy;
- backup/restore fixtures remain readable by the new connection layer.

Rollback: old code ignores the additive Index tables and can use the existing constructors without a down-migration. If the new tables themselves must be removed from an operator database, restore the verified pre-migration backup; never drop them in place as an automatic rollback. Disposable fixture databases may be recreated. No database filename changes occur.

### P0-D — Search boundary, projection, and incremental identity

Deliverables:

- generic `AssetSearchResult` projection;
- additive `search_assets(..., asset_types=...)` and `index_assets(...)` service methods;
- legacy `search_skills`/`index_skills` wrappers fixed to `asset_type=skill`;
- API threadpool offload for synchronous model/search work with a bounded concurrency policy;
- SQL queries that omit `raw_json` from search and list hot paths;
- additive index-state identity containing asset/revision, parser ID/version, representation version, embedding model ID/version, and content hash;
- incremental index path that embeds only changed/missing representations.

Acceptance:

- a second index run over unchanged input performs zero new embeddings;
- parser or representation version drift selects only affected revisions;
- HTTP cancellation/timeout does not corrupt the existing index;
- an event-loop responsiveness test proves a concurrent lightweight request is served while search work runs;
- existing Skill search routes preserve response compatibility.
- the deterministic concurrency fixture uses two workers and a queue capacity of four: while a stub search blocks for one second, a lightweight health request completes within 250 ms in at least 9 of 10 runs; once workers and queue are saturated, the next request fails with the documented overload response within 250 ms and performs no index write.

Rollback: wrappers can route to the existing full indexer; additive index-state data is derived and disposable.

### P0-E — Drift doctor and conditional read-only Asset API

Entry/cut line: the doctor work is required. The Asset API sub-batch begins only after P0-B through P0-D pass all focused gates and two consecutive full Python regression runs without a corrective code change between them. Otherwise defer all new Asset endpoints to P1; that deferral does not block completion of the P0 storage foundation.

Deliverables:

- additive read-only endpoints:
  - `GET /api/assets`;
  - `GET /api/assets/{asset_id}`;
  - `GET /api/assets/{asset_id}/revisions`;
  - `POST /api/assets/search`;
- legacy `/api/skills` endpoints implemented as Skill-filtered compatibility surfaces;
- revision-aware projection drift report evolved from `tools/report_db_identity_drift.py`;
- doctor fields for pending projection, stale index identity, duplicate canonical identity, and model/version drift.

Deferred from this batch:

- evaluations, approvals, and relations endpoints unless backed by an approved Asset schema;
- mutation endpoints;
- Dashboard component renames.

Acceptance:

- new Asset endpoints expose only projections unless the detail endpoint explicitly requests payload content;
- no Asset endpoint can change governance or Runtime state;
- the doctor distinguishes healthy, stale-derived-projection, authority-missing, and unknown states;
- compatibility tests cover both Asset and Skill routes.

Rollback: remove the additive router; legacy routes remain available.

### P0-F — Integrated verification and P1 decision packet

Required gates:

```powershell
.\.venv\Scripts\python.exe -m compileall api asset_registry runtime vector_db tools scripts skill-0-dashboard/apps/api -q
.\.venv\Scripts\python.exe tools\check_doc_status_markers.py
.\.venv\Scripts\python.exe tools\check_shared_docs.py
.\.venv\Scripts\python.exe tools\validate_skill_schema.py parsed
.\.venv\Scripts\python.exe -m pytest tests skill-0-dashboard/apps/api/tests -q --timeout=120
npm run lint
npm test
npm run build:ci
git diff --check
```

Additional evidence:

- migration equivalence report;
- incremental index run with changed/unchanged counts;
- event-loop responsiveness result;
- Registry/Index drift doctor examples;
- legacy route compatibility matrix;
- no-secret and no-database-artifact diff scan.

P0 is complete only if all Core gates pass and no real adapter, non-dry-run behavior, physical topology/data migration, or public deployment was introduced. The explicitly allowed additive Index migration is reported separately and does not imply a topology decision.

## 8. API compatibility map

| Existing surface | P0 behavior | New surface |
|---|---|---|
| `GET /api/skills` | Wrapper filtered to `asset_type=skill` | Conditional P0-E `GET /api/assets` |
| `GET /api/skills/{id}` | Resolve through Skill compatibility identity | Conditional P0-E `GET /api/assets/{asset_id}` |
| `POST/GET /api/search` | Preserve current request/response | Conditional P0-E `POST /api/assets/search` |
| `POST /api/index` | Preserve authenticated legacy operation | Internal `index_assets`, with public mutation route deferred |
| Runtime `skill_id` fields | Preserve current contract in P0 | Asset identity stays outside Runtime ledger migration |

No removal timetable is set in P0. Deprecation requires usage evidence, a versioned contract, and a separately approved migration.

## 9. Database strategy for this round

P0 keeps the current physical names and treats them as logical adapters:

| Current file | P0 logical role | Authority |
|---|---|---|
| `governance.db` | Legacy Registry/Governance adapter | Revision and approval authority |
| `skills.db` | Legacy Search Index adapter | Derived, rebuildable projection |
| `runtime.db` | Runtime Ledger | Append-only execution authority |

P0 may add only the two checksum-migrated Index tables listed in P0-C. It must not add DDL to operator Governance/Runtime stores, copy governance rows into `skills.db`, merge Runtime history, or claim a final physical topology.

The P1 database decision must be based on:

- migration and rollback rehearsal;
- backup/recovery unit design;
- measured writer contention;
- index rebuild duration and artifact size;
- operator complexity;
- FTS5/sqlite-vec benchmark results.

## 10. Risk register

| Risk | Control |
|---|---|
| Generic naming accidentally changes Skill semantics | Compatibility classification and golden fixtures before replacement |
| Registry abstraction becomes multi-engine overengineering | SQLite-only protocols; no alternate backend in P0 |
| Asset envelope conflicts with ARD/runtime contract | ADR-0004/0006 invariants and contract tests |
| Migration runner corrupts legacy databases | Fixture copies, checksum gate, no import-time migration, backup/restore test |
| Async offload hides unbounded model work | Bounded worker, timeout/cancellation tests, request metrics |
| Incremental index serves stale data | Revision/content/model identity plus doctor-visible drift |
| Physical DB decision is made without evidence | Explicit P0 deferral and P1 decision packet |
| Scope expands into Dashboard/parser/real adapters | Non-goals and batch acceptance gates |

## 11. P1 reopen candidates

P0-F may recommend, but must not implement, these P1 items:

1. `runtime_assets`, `asset_revisions`, representations, relations, evaluations, approvals, and index outbox.
2. Physical `registry.db + index.db + runtime.db` versus `assets.db + runtime.db` decision.
3. FTS5 plus sqlite-vec hybrid retrieval and score fusion.
4. Workflow ground-truth corpus and second parser adapter.
5. Dashboard `AssetShell` and type-specific panels.
6. Moving `parsed/` to normalized build artifacts.
7. Legacy Skill API deprecation policy.

Each item requires its own evidence and approval gate.

## 12. Definition of done

The next round is done when:

- the two ADRs and Runtime Asset Envelope are accepted and tested;
- existing Skill behavior is preserved through explicit adapters;
- Runtime no longer scans the parsed directory on every create/resume request;
- search/model work no longer blocks the API event loop directly;
- unchanged content is not re-embedded;
- search/list SQL does not fetch raw payloads unnecessarily;
- migration checksums and connection policies are testable and observable;
- the drift doctor distinguishes authority failures from stale derived state;
- all current and new regression gates pass;
- a bounded P1 decision packet exists without performing the P1 migration.

## 13. Recommended execution order

Execute one reviewed commit series per batch:

```text
P0-A contracts
  -> P0-B repository boundary
  -> P0-C migration/connection foundation
  -> P0-D search/index hardening
  -> P0-E Asset API/doctor
  -> P0-F integrated verification and P1 decision
```

Any failed batch acceptance criterion blocks every downstream batch. Stop further mutation immediately, preserve the first failure evidence, and perform only the read-only diagnostics needed to classify it before attempting a corrective replacement run.

## 14. Execution log

- `P0-A` completed on `2026-07-17`: ADR-0007/0008, Envelope v1,
  compatibility map, semantic failure fixtures, and contract tests were added.
  Focused contract/document verification passed (`27 passed`).
- `P0-B` completed on `2026-07-17`: the immutable legacy corpus repository,
  explicit Skill adapter, available/ambiguous identity map, stale snapshot guard,
  and Runtime dependency binding replaced request-time JSON enumeration. The
  checked-in corpus remains `196/196` schema-valid; focused repository, contract,
  and Runtime API verification passed (`48 passed`).
- `P0-C` completed on `2026-07-17` for code and fixture boundaries only: named
  SQLite policies, explicit existing/read-only versus maintenance modes,
  checksum-aware migrations, classified contention, and integrity-checked
  backup/restore were added. No operator database was migrated. Focused storage
  and Core API verification passed (`48 passed`).
- `P0-D` completed on `2026-07-17`: synchronous search/index work is offloaded
  through a two-worker/four-queue bounded executor, saturation fails fast without
  releasing capacity on caller cancellation, search/list hot paths omit raw
  payloads, and revision/model/representation identity drives atomic incremental
  reconciliation. Unchanged second runs embed zero items; drift, removal, and
  injected-failure fixtures passed. Focused search/index/API verification passed
  (`66 passed`).
- `P0-E` completed on `2026-07-17`: two consecutive full Python regressions
  passed with no corrective change between them (`403 passed` each), opening the
  conditional API cut line. Read-only Asset list/detail/revision/search surfaces
  and a schema-versioned drift doctor were then added. The doctor classifies
  healthy, stale-derived-projection, authority-missing, and unknown with stable
  exit codes. Current local operator evidence is intentionally
  `authority-missing` (exit `2`) because no Governance operator DB or migrated
  Asset index exists; this is observed state, not an implicit migration request.
- `P0-F` completed on `2026-07-17`: integrated gates passed (`414` Python tests,
  `196` parsed schemas, `34` frontend tests, lint, build, and bundle guard). The
  P1 decision packet records NO-GO for physical DB reorganization, FTS5, a
  second Asset Type, and Dashboard rename until their evidence gates are met.
