# Skill-0 P0 Repair Plan

Updated: `2026-03-27`
Status: `complete locally - batches A through D implemented`
Scope: `P0 only`
Authority: `current working repair plan`

Execution status:
- Batch A complete: governance in-place revision mutation closed and callers updated.
- Batch B complete: helper/API/version drift aligned to canonical `v2.4.0`.
- Batch C complete: parser and search-consumer paths now operate on canonical fields, and the checked-in `parsed/` corpus no longer carries legacy rule/directive aliases.
- Batch D complete: historical docs are demoted, review-bundle authority is indexed, and current-facing docs no longer compete silently with archival material.

## 1. Purpose

This plan records the remaining P0 issues after the first contract-drift cleanup pass and defines one coordinated repair batch for fixing them together.

The target is not to add features. The target is to close the P0 baseline promised in:

- canonical contract recovery
- artifact-centric governance redesign
- external review baseline refresh

## 2. Search-First Audit Scope

The audit pass covered:

- parser and schema helpers
- checked-in parsed dataset
- vector search/embedder consumers
- core API and dashboard API/web contracts
- governance DB semantics and maintenance scripts
- CI validation
- README / AGENTS / reference and review-facing docs
- P0-relevant tests

## 3. Confirmed Baseline

### Already in place

- `parsed/` validates cleanly against the live schema.
- CI already runs `python tools/validate_skill_schema.py parsed`.
- revision-aware governance tables and UI fields exist.
- contract decision / compatibility / validation docs now exist.
- the first README / AGENTS / batch-parse drift cleanup pass has landed locally.

### Still blocking a clean P0 close

1. Governance still allows in-place mutation of the current revision.
2. Active helper/test code still emits and validates legacy `2.0.0` / legacy-field shapes.
3. Some runtime/API/analyzer surfaces still report stale `2.1.0` version strings.
4. Some parsers/consumers still accept or construct legacy intermediates too quietly.
5. Review-facing docs are not yet consistently classified as authoritative vs historical.
6. Governance migration/API/audit semantics are implemented in code, but not yet documented as a formal deliverable.

## 4. Issue Register

### P0-01 High

**Title:** `update_skill()` mutates the current revision in place

**Why it matters**

P0-B defines governance around immutable artifacts and revision-level traceability. Directly editing the current revision breaks that model.

**Evidence**

- [governance_db.py](/home/miles/dev2/skill-0/tools/governance_db.py#L844)
- [governance_db.py](/home/miles/dev2/skill-0/tools/governance_db.py#L909)
- [governance_db.py](/home/miles/dev2/skill-0/tools/governance_db.py#L927)

**Observed behavior**

- `update_skill()` accepts revision fields such as `source_path`, `source_commit`, `version`, `risk_score`, `equivalence_score`, and `installed_path`
- those fields are written directly into `skill_revisions`
- the same call also projects them back into `skills`

**Impact**

- audit can no longer distinguish “new artifact” from “current artifact edited in place”
- approval/test/scan evidence can drift under the same revision id

### P0-02 High

**Title:** `scripts/helper.py` and its tests still define the old schema as operative

**Why it matters**

This is active code, not archival prose. It can still generate legacy artifacts and train tests on the wrong contract.

**Evidence**

- [helper.py](/home/miles/dev2/skill-0/scripts/helper.py#L62)
- [helper.py](/home/miles/dev2/skill-0/scripts/helper.py#L178)
- [helper.py](/home/miles/dev2/skill-0/scripts/helper.py#L340)
- [test_helper.py](/home/miles/dev2/skill-0/tests/test_helper.py#L243)

**Observed behavior**

- validator warns unless `schema_version == 2.0.0`
- generated templates still use `schema_version: 2.0.0`
- generated templates still use legacy `skill_id` shape
- rules are still described with legacy `condition` / `output`
- tests assert the old template/version behavior

### P0-03 High

**Title:** Core API still reports `2.1.0` as the current public version

**Why it matters**

P0-A requires outward-facing contract and version wording to stop drifting.

**Evidence**

- [main.py](/home/miles/dev2/skill-0/api/main.py#L148)
- [test_api_core.py](/home/miles/dev2/skill-0/tests/integration/test_api_core.py#L74)
- [test_api_core.py](/home/miles/dev2/skill-0/tests/integration/test_api_core.py#L92)

**Observed behavior**

- OpenAPI metadata still says `2.1.0`
- integration tests still lock the root and health-detail version to `2.1.0`

**Decision needed**

- either treat API version as intentionally separate from schema version and document that
- or move the public API baseline to a new single source-of-truth constant

### P0-04 Medium

**Title:** Backfill and utility scripts still route artifact changes through `update_skill()`

**Evidence**

- [backfill_empty_fields.py](/home/miles/dev2/skill-0/tools/backfill_empty_fields.py#L162)
- [backfill_governance.py](/home/miles/dev2/skill-0/tools/backfill_governance.py#L129)
- [backfill_source_urls.py](/home/miles/dev2/skill-0/tools/backfill_source_urls.py#L126)

**Impact**

- even if runtime paths become revision-safe, maintenance scripts can still reintroduce mutable-record drift

### P0-05 Medium

**Title:** Analyzer/export version strings still anchor operational metadata to `2.1.0`

**Evidence**

- [advanced_skill_analyzer.py](/home/miles/dev2/skill-0/tools/advanced_skill_analyzer.py#L547)
- [scans.py](/home/miles/dev2/skill-0/skill-0-dashboard/apps/api/routers/scans.py#L249)

**Impact**

- export artifacts and scan surfaces still project stale version metadata

### P0-06 Medium

**Title:** `reference.md` is still materially misleading, not just historically old

**Evidence**

- [reference.md](/home/miles/dev2/skill-0/reference.md#L1)
- [reference.md](/home/miles/dev2/skill-0/reference.md#L23)
- [reference.md](/home/miles/dev2/skill-0/reference.md#L40)
- [reference.md](/home/miles/dev2/skill-0/reference.md#L125)

**Observed behavior**

- the top note says the file reflects an older baseline
- the body still teaches obsolete `skill_id`, `schema_version`, and rule-field semantics as if they were current

**Impact**

- the file is still easy for humans or agents to misread as the live schema reference

### P0-07 Medium

**Title:** `batch_parse.py` and `vector_db/embedder.py` still rely on legacy-shape tolerance

**Evidence**

- [batch_parse.py](/home/miles/dev2/skill-0/tools/batch_parse.py#L289)
- [embedder.py](/home/miles/dev2/skill-0/vector_db/embedder.py#L99)
- [embedder.py](/home/miles/dev2/skill-0/vector_db/embedder.py#L111)
- [embedder.py](/home/miles/dev2/skill-0/vector_db/embedder.py#L123)

**Observed behavior**

- parser rules are still initially constructed with legacy `condition` / `output`
- embedder still quietly falls back to legacy keys like `type`, `mode`, `condition`, and `content`

**Impact**

- canonical recovery is weaker than it looks because consumers still silently accept the old dialect

### P0-08 Medium

**Title:** Governance redesign deliverables are missing as explicit docs

**Why it matters**

Revision-aware governance exists in code and tests, but not yet as a concise reviewable design note.

**Needed docs**

- governance migration / backfill note
- revision-aware API semantics note
- audit semantics note clarifying what binds to `skill_id` vs `revision_id`

### P0-09 Medium

**Title:** Some current-facing review/progress docs are contradicted by newer evidence

**Evidence**

- [project-progress-report-2026-03-23.md](/home/miles/dev2/skill-0/docs/project-progress-report-2026-03-23.md#L97)
- [project-progress-report-2026-03-23.md](/home/miles/dev2/skill-0/docs/project-progress-report-2026-03-23.md#L98)
- [project-progress-report-2026-03-23.md](/home/miles/dev2/skill-0/docs/project-progress-report-2026-03-23.md#L101)
- [implementation-summary.md](/home/miles/dev2/skill-0/docs/implementation-summary.md#L148)
- [implementation-summary.md](/home/miles/dev2/skill-0/docs/implementation-summary.md#L194)

**Examples**

- says Recent Activity is still a placeholder
- says Bulk Approve is disabled
- says frontend JWT/session appears incomplete
- says validation passed against `v2.0.0`
- says the project analyzed `32` parsed skills

### P0-10 Low

**Title:** Historical documents are not yet centrally classified

**Examples**

- [reference.md](/home/miles/dev2/skill-0/reference.md)
- dated review snapshots under `docs/`
- comparison docs that contain period-specific counts

**Impact**

- not a runtime issue
- still weakens P0-F because external readers cannot quickly tell “historical context” from “current authority”

## 5. One-Shot Repair Batches

### Batch A: Governance Immutability Enforcement

**Goal**

Make artifact-changing updates revision-safe by default.

**Changes**

1. Restrict `update_skill()` to true skill-row metadata only.
2. Reject artifact-level revision mutations through `update_skill()` with a clear error path.
3. Route artifact changes through `register_revision()` instead.
4. Update maintenance/backfill scripts that currently mutate artifact fields in place.
5. Add regression tests proving artifact-level mutation no longer happens via `update_skill()`.

**Files**

- `tools/governance_db.py`
- backfill/utility scripts that call `update_skill()`
- focused tests in `tests/`

### Batch B: Contract And Version Source Of Truth

**Goal**

Stop outward-facing `2.0.0` / `2.1.0` drift in active code and tests.

**Changes**

1. Decide and centralize the current public API/analyzer version values.
2. Update `api/main.py` root/OpenAPI/health/version surfaces.
3. Update matching integration tests.
4. Update analyzer/export fallback version strings.
5. Update `scripts/helper.py` to emit canonical template/version data.
6. Update `tests/test_helper.py` to assert the canonical contract rather than the historical helper shape.

### Batch C: Parser And Consumer Canonicalization

**Goal**

Reduce silent legacy-shape dependence after dataset normalization.

**Changes**

1. Make `tools/batch_parse.py` emit canonical rule fields directly.
2. Review embedder fallback behavior and prefer canonical-only reads where safe.
3. Add tests proving canonical artifacts are sufficient for parser/search consumers.
4. Keep normalization/fallbacks only where they remain an intentional migration aid.

### Batch D: Documentation And Review-Bundle Cleanup

**Goal**

Make current docs trustworthy without rewriting history.

**Changes**

1. Classify each major doc as:
   - authoritative current baseline
   - historical context
   - conceptual pressure-test
2. Rewrite or demote `reference.md` so it cannot be mistaken for the live schema reference.
3. Refresh current-facing docs that still state obsolete facts.
4. Add governance migration/API/audit notes.
5. Add an index doc for the authoritative review bundle if needed.

## 6. Execution Order

1. Batch A: governance immutability enforcement
2. Batch B: contract/version source-of-truth cleanup
3. Batch C: parser/consumer canonicalization
4. Batch D: documentation and review-bundle cleanup
5. verification pass

## 7. Verification Plan

### Required checks

```bash
.venv/bin/python tools/validate_skill_schema.py parsed
.venv/bin/python -m pytest tests/test_schema_contract.py tests/test_governance_revisions.py tests/test_helper.py tests/integration/test_api_core.py -q
.venv/bin/python -m pytest skill-0-dashboard/apps/api/tests -q
```

### Acceptance criteria

- artifact-changing updates no longer mutate an existing revision in place
- helper/template code no longer emits legacy `2.0.0` contract shapes
- no live API surface still reports `2.1.0` as the current baseline unless explicitly documented as an intentional decoupled API version
- parser/search consumers no longer depend on silent legacy-shape fallback where canonical fields already exist
- governance semantics are documented in reviewable Markdown
- current review bundle docs no longer contradict each other
- historical docs are clearly labeled instead of silently mixed with live reference material

## 8. Explicitly Deferred To P1

These were found in the audit but should not be mixed into the P0 batch except where compatibility notes require brief mention:

- broader `equivalence_*` to `fidelity_*` naming convergence
- benchmark/evaluation/failure-corpus work
- P2 search calibration
