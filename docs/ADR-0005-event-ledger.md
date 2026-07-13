# ADR-0005 — Append-only runtime event ledger

**Status:** Proposed

## Decision

Record runtime decisions, action effects, external resource IDs, compensation attempts, and terminal outcomes as append-only events. Maintain `runtime_runs.status` only as a projection updated in the same transaction as the event.

## Rationale

Agent/checkpoint state cannot prove whether an external side effect committed. Recovery must be reconstructable after a process restart.

## Initial storage

SQLite with foreign keys, synchronous FULL, and conservative DELETE journal mode by default. WAL is an explicit deployment choice after SQLite-version and backup review.
