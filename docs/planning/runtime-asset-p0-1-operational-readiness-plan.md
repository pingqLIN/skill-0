# Runtime Asset P0.1 Operational Readiness Plan

- Status: **In execution**
- Date: `2026-07-18`
- Authority: Runtime v4 remains dry-run only; P0 contracts remain additive
- Traditional Chinese companion: [`runtime-asset-p0-1-operational-readiness-plan.zh-tw.md`](runtime-asset-p0-1-operational-readiness-plan.zh-tw.md)

## Objective

Close the operational gap between the verified P0 implementation and a usable
local derived Index without inventing Governance approval. The public checkout
contains no operator authority database, and its root `skills.db` and
`governance.db` files are unrelated sample databases.

## Batches

1. **P0.1-A identity:** derive unique canonical Asset IDs for the three Java
   upgrade payloads from explicit source identity while preserving their shared
   ambiguous legacy alias and byte-identical payloads.
2. **P0.1-B maintenance tooling:** add an audited Index preflight, migration
   preview, verified backup, apply, incremental index, second no-op run, and
   doctor evidence command.
3. **P0.1-C rehearsal:** exercise the workflow against disposable copies, then
   create a local rebuildable Index only after backup and verification.
4. **P0.1-D acceptance:** run contract, compatibility, migration, search,
   Runtime, schema, documentation, and full regression gates.

## Authority boundary

`governance/db/governance.db` is the only operator Governance path. P0.1 will
not copy the root sample database, synthesize bindings, or approve revisions to
make the doctor green. The local doctor may therefore remain
`authority-missing` even when identity and Index projection are healthy. A
`healthy`/0 result is required on an approved Governance fixture and on a real
operator store only after genuine review decisions exist.

## Rollback

Every operator Index mutation requires an integrity-checked SQLite backup. An
invalid legacy target is replaced only because the Index is derived and only
after preserving that target. Rollback restores the verified backup while
writers are quiesced; tables are never dropped in place. Governance and Runtime
stores are not migrated.
