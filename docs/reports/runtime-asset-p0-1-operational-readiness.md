# Runtime Asset P0.1 Operational Readiness Evidence

- Status: **Derived Index operational; Governance acceptance intentionally not claimed**
- Date: `2026-07-18`
- Plan: [`../planning/runtime-asset-p0-1-operational-readiness-plan.md`](../planning/runtime-asset-p0-1-operational-readiness-plan.md)
- Traditional Chinese companion: [`runtime-asset-p0-1-operational-readiness.zh-tw.md`](runtime-asset-p0-1-operational-readiness.zh-tw.md)

## Outcome

The checked-in corpus now resolves to 196 unique canonical Asset IDs. The three
Java upgrade payloads retain their byte-identical legacy Skill payload and one
ambiguous legacy alias, while Runtime and Governance receive their unique
canonical Asset IDs. True canonical, derived, or alias-namespace collisions
still fail closed.

An audited maintenance CLI now preflights the existing Index schema, previews
checksum migrations read-only, creates a non-overwriting SQLite backup, applies
only approved Index migrations, runs incremental indexing twice, and reports
doctor evidence. Strict mode refuses authority/canonical/checksum/unknown
failures before indexing and succeeds only with a healthy post-index doctor.

## Local Index rehearsal

The pre-existing root `skills.db` was not an Index; it contained only a sample
table. It was preserved in two recoverable forms before replacement:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `.del/skills.sample.20260717T170129Z.db` | 8,192 | `d1c2813b32157f2021c583e156a7a783ca5d644ba8912cb633ad9d5f52a87f37` |
| `backups/skills.sample-pre-p0-1.20260717T170129Z.db` | 8,192 | `d929625e8968662862f072f28f2d89a3d35f77d87998a93065208eca0ac26868` |

A disposable valid Index then passed preview, backup, migration, index, and
restore rehearsal. The same guarded process created the local derived
`skills.db`. Its pre-migration backup is
`backups/skills.pre-asset-migration.20260717T170129Z.db`, 49,152 bytes, SHA-256
`d590d3b0cc86ca978f8e57439d87334e005280003e16bcd9db6c668502789077`.
Restoring that backup into a separate database produced the same hash and a
valid pending-migration preview.

## Index evidence

| Check | Result |
|---|---|
| Migration | `001_asset_index_state` applied with recorded checksum |
| SQLite integrity | `ok` |
| First incremental run | total `196`, changed `196` |
| Second incremental run | changed `0`, unchanged `196`, removed `0` |
| Index rows | `196` |
| Pending projection | `0` |
| Stale identity | `0` |
| Duplicate canonical identity | `0` |
| Ambiguous legacy alias | `1`, intentionally fail-closed for legacy detail lookup |
| Search smoke | `document processing` returned canonical PDF/Docx-related Asset projections |
| Model identity | `all-MiniLM-L6-v2`, full local-model digest recorded in evidence |

The ignored local evidence is under
`audit/p0-1/operator-*-20260717T170129Z.json` and
`.artifacts/p0-1/20260717T170129Z/`.
The search projection and model identity are captured specifically in
`audit/p0-1/operator-index-search-20260717T170129Z.json`.

## Governance boundary

The public checkout has no `governance/db/governance.db`. P0.1 did not copy the
unrelated root sample database, synthesize canonical bindings, or approve any
revision. The local index command therefore ran only with the explicit
`--allow-nonhealthy-evidence` flag and correctly recorded:

- `accepted=false`;
- `rehearsal_only=true`;
- doctor `authority-missing`, exit `2`;
- one reason: `governance_database_missing`.

This is a truthful authority boundary, not an Index failure. Strict operator
acceptance remains blocked until genuine reviewed Governance revisions exist.

## Acceptance evidence

The full checked-in corpus passed a test-only end-to-end doctor fixture with:

| Gate | Result |
|---|---|
| Registry revisions | `196` |
| Unique canonical identities | `196`; duplicate canonical `0` |
| Index state rows | `196`; pending/stale/model drift `0` |
| Migration status | approved checksum recorded as `applied` |
| Governance bindings | `196` matching approved-current revision digests |
| Doctor | `healthy`, exit `0` |

The fixture exists only in the test temporary directory and is never an
operator authority source. The local operator-facing doctor remains
`authority-missing`, exit `2`, because no reviewed Governance database exists.
Accordingly, P0.1 technical acceptance is complete while operator acceptance
is an explicit **NO-GO**.

## Rollback

Quiesce Index writers, validate the selected backup, then restore the verified
pre-migration backup. Do not drop migration tables in place. Governance and
Runtime stores were not mutated.
