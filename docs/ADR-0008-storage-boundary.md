# ADR-0008 — Registry, Index, and Runtime storage boundary

**Status:** Accepted for P0

## Context

The current implementation combines a checked-in canonical corpus, governance
revision authority, a rebuildable vector projection, and an append-only Runtime
ledger across existing files and inline schema setup. A physical database
reorganization is not yet justified by migration or workload evidence.

## Decision

P0 introduces three logical boundaries while preserving physical filenames:

| Boundary | P0 adapter | Authority |
|---|---|---|
| Registry | canonical corpus plus governance revision lookup | Asset identity and approved revision |
| Index | `skills.db` compatibility adapter | Derived, disposable search projection |
| Runtime | `runtime.db` | Append-only execution evidence |

Repositories are SQLite-specific and narrow; P0 does not add a storage-engine
plugin abstraction. Connections are created per unit of work with named policy.
Migrations are ordered, transactional, and checksum-aware. API import never
migrates an operator database.

Only `schema_migrations` and `asset_index_state` are permitted as additive P0
DDL in `skills.db`, and only through an explicit preview, verified backup, and
L3 checkpoint. P0 applies no operator DDL to Governance or Runtime stores.

The Index is never execution authority. Registry-to-Index publication direction
is explicit and doctor-visible; a stale projection fails classified health
checks but cannot change governance or Runtime state. An outbox is a P1 option,
not a P0 requirement.

## Snapshot freshness

Each process owns one immutable, versioned corpus snapshot. A live-corpus digest
check is required before Runtime create or resume. If it differs from the active
snapshot, the request fails closed as `stale_source_snapshot`; doctor reporting
alone is not sufficient. An explicit authenticated reload validates a complete
replacement map and atomically swaps it. Ambiguous canonical IDs remain recorded
as conflicts so the snapshot can serve non-ambiguous assets without selecting a
duplicate.

## Index-state lifecycle

Index identity is unique over asset ID, Asset revision ID, representation
version, embedding model ID, and embedding model version. Each state row binds
the concrete legacy `skills.id` and vector row. Vector mutation and state update
share one transaction. Clear/reindex removes derived state with vector rows;
filename reuse with a changed Asset ID replaces the old projection; source
disappearance marks/removes the projection; interrupted or orphaned state is
doctor-visible and repaired only by an explicit rebuild.

## Physical topology deferral and rollback

Renaming, splitting, merging, or copying authority rows between physical
databases is deferred to P1. New code can route back through compatibility
adapters and derived state may be rebuilt. Operator DDL is never rolled back by
dropping tables in place; a verified pre-migration backup is restored.
